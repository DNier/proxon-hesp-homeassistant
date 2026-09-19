"""Offline comparison preserves observations and uncertainty."""

import json

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.compare_captures import changed_bits, compare, main, render
from tools.inventory_capture import load_capture

OFF = bytes.fromhex("118000f80100000800000000a1fd")
ON = bytes.fromhex("118000f8010000084000000030b0")


def capture(*items, **metadata):
    return {"chunks": [{"elapsed_ms": t, "hex": b.hex()} for t, b in items], **metadata}


def test_intensive_transitions_counts_bits_and_event():
    report = compare(
        capture((0, OFF), (5, OFF)),
        capture((10, OFF), (20, ON), (25, ON), (30, OFF)),
        after_event={"elapsed_ms": 18, "description": "BDE button"},
    )
    group = report["after"]["groups"]["118000/0x01F8/4"]
    assert group["count"] == 4
    assert group["transition_count"] == 2
    assert group["payload_counts"] == {"00000000": 2, "40000000": 2}
    assert group["changes"][1]["changed_bits"] == [
        {"byte": 0, "bit": 6, "before": 0, "after": 1}
    ]
    assert group["changes"][1]["event_delta_ms"] == 2
    # A return to the original value must not hide the intervening transition.
    assert not report["groups"]["118000/0x01F8/4"]["same_observed_sequence"]
    assert "correlation" in render(report)
    assert '"elapsed_ms": 20' in render(report)


def test_windows_parse_full_stream_and_use_completion_time():
    source = capture((0, OFF + ON[:6]), (10, ON[6:]), (20, OFF))
    report = compare(source, source, before_window=(0, 10), after_window=(10, 20))
    key = "118000/0x01F8/4"
    assert report["before"]["groups"][key]["values"] == ["00000000"]
    assert report["after"]["groups"][key]["values"] == ["40000000"]
    assert report["groups"][key]["changed_bits"][0]["bit"] == 6


def test_unknown_selector_size_missing_corruption_and_noise():
    def frame(header):
        body = bytes.fromhex(header)
        return body + checksum(body).to_bytes(2, "little")

    other = frame("998009f80100000201")
    selector = frame("118001f80100000840000000")
    short = frame("118000f80100000201")
    corrupt = ON[:-1] + bytes([ON[-1] ^ 1])
    report = compare(
        capture((0, OFF)),
        capture((0, b"noise" + corrupt), (42, other + selector + short + ON[:6])),
    )
    assert report["groups"]["118000/0x01F8/4"]["presence"] == "only_before"
    for key in ("998009/0x01F8/1", "118001/0x01F8/4", "118000/0x01F8/1"):
        assert report["groups"][key]["presence"] == "only_after"
    assert report["after"]["unparsed_bytes"] == 5 + len(corrupt) + 6
    assert report["after"]["max_chunk_gap_ms"] == 42
    assert changed_bits("00", "0000") is None


@pytest.mark.parametrize("window", [(-1, None), (0, 0), (2, 1), (True, 2)])
def test_invalid_window(window):
    with pytest.raises(ValueError):
        compare(capture(), capture(), before_window=window)


def test_empty_window_is_not_unchanged_and_metadata_is_visible():
    report = compare(
        capture((0, OFF), status="recording"),
        capture((0, OFF), status="manual"),
        after_window=(1, 2),
    )
    assert report["groups"]["118000/0x01F8/4"]["presence"] == "only_before"
    assert report["metadata_differences"] == ["status"]
    assert compare(capture(), capture())["groups"] == {}


def test_cli_and_legacy_wrappers(tmp_path, monkeypatch):
    data = capture((0, OFF), (10, ON))
    for wrapper in (data, {"capture": data}, {"data": {"capture": data}}):
        source = tmp_path / "capture.json"
        source.write_text(json.dumps(wrapper))
        assert load_capture(source) == data
    output, report = tmp_path / "result.json", tmp_path / "report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "compare",
            str(source),
            "--before-end-ms",
            "10",
            "--after-start-ms",
            "10",
            "--output",
            str(output),
            "--report",
            str(report),
        ],
    )
    main()
    assert json.loads(output.read_text())["after"]["frames"] == 1
    assert "40000000" in report.read_text()
    monkeypatch.setattr(
        "sys.argv",
        ["compare", str(source), "--output", str(source), "--report", str(report)],
    )
    with pytest.raises(SystemExit):
        main()
    assert load_capture(source) == data
