"""Offline shape comparison must not imply transactions or readable types."""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.audit_recorded_queries import audit, inventory, main

FRAMES = {
    key: bytes.fromhex(value)
    for key, value in json.loads(
        (Path(__file__).parent / "fixtures" / "controller_frames.json").read_text()
    ).items()
}
FILTER_QUERY = bytes.fromhex("108000ed000000040100734a")
BYPASS_QUERY = bytes.fromhex("1080006001000004010049e1")


def frame(header, dp, payload):
    body = (
        bytes.fromhex(header)
        + dp.to_bytes(2, "little")
        + b"\x00\x00"
        + bytes([len(payload) * 2])
        + payload
    )
    return body + checksum(body).to_bytes(2, "little")


def capture(*data):
    return {
        "chunks": [
            {"elapsed_ms": index * 10, "hex": item.hex()}
            for index, item in enumerate(data)
        ]
    }


@pytest.mark.parametrize(
    ("query_hex", "dp", "argument", "size"),
    [
        ("108000ed000000040100734a", "0x00ed", 1, 4),
        ("1080006001000004010049e1", "0x0160", 1, 1),
        ("108000300300000400004ef8", "0x0330", 0, 4),
        ("108000780100000406008af1", "0x0178", 6, 12),
        ("108000d602000004140098f6", "0x02d6", 20, 40),
        ("108000df020000041c00270c", "0x02df", 28, 112),
        ("1080001d05000004020082e8", "0x051d", 2, 4),
        ("108000d70000000402005c81", "0x00d7", 2, 8),
    ],
)
def test_recorded_queries_and_existing_recorded_response_shapes(
    query_hex, dp, argument, size
):
    source = capture(bytes.fromhex(query_hex), FRAMES[dp])
    report = audit(source)
    item = report["queries"][0]
    identity = f"224000/{dp.upper().replace('0X', '0x')}/{size}"
    assert item["request_argument"] == argument
    assert item["expected_response_identity"] == identity
    assert item["response_status"] == "observed"
    assert item["response_observation"] == {
        "identity": identity,
        "count": 1,
        "first_seen_ms": 10,
        "last_seen_ms": 10,
    }
    assert item["other_same_dp_groups"] == []
    assert report["overview"]["unparsed_bytes"] == 0


@pytest.mark.parametrize(
    ("header", "dp", "payload", "other_identity"),
    [
        ("224007", 0x00ED, b"\0" * 4, "224007/0x00ED/4"),
        ("118000", 0x00ED, b"\0" * 4, "118000/0x00ED/4"),
        ("224000", 0x00ED, b"\0" * 2, "224000/0x00ED/2"),
        ("234000", 0x00ED, b"", "234000/0x00ED/0"),
        ("224000", 0x00EE, b"\0" * 4, None),
    ],
)
def test_wrong_header_length_ack_and_dp_do_not_match(
    header, dp, payload, other_identity
):
    report = audit(capture(FILTER_QUERY, frame(header, dp, payload)))
    item = report["queries"][0]
    assert item["expected_response_identity"] == "224000/0x00ED/4"
    assert item["response_status"] == "not_observed"
    assert item["response_observation"] is None
    assert [value["identity"] for value in item["other_same_dp_groups"]] == (
        [other_identity] if other_identity is not None else []
    )
    assert report["overview"]["unparsed_bytes"] == 0


@pytest.mark.parametrize(("dp", "argument"), [(0xFFFF, 1), (0x00ED, 2)])
def test_unknown_dp_or_argument_has_no_inferred_response_type(dp, argument):
    source = capture(
        frame("108000", dp, argument.to_bytes(2, "little")),
        frame("224000", dp, b"\0" * 4),
    )
    item = audit(source)["queries"][0]
    assert item["response_status"] == "unsupported_query_shape"
    assert item["expected_response_identity"] is None
    assert item["response_observation"] is None
    assert len(item["other_same_dp_groups"]) == 1


def test_repeated_responses_before_query_are_only_capture_cooccurrence():
    report = audit(capture(FRAMES["0x00ed"], FRAMES["0x00ed"], FILTER_QUERY))
    item = report["queries"][0]
    assert item["occurrences"] == 1
    assert item["response_observation"]["count"] == 2
    assert item["response_status"] == "observed"
    assert "Co-occurrence" in report["association_basis"]
    assert "no causal or one-to-one" in report["association_basis"]


def test_each_fragment_split_uses_existing_parser_and_completion_timestamp():
    raw = FILTER_QUERY + FRAMES["0x00ed"]
    for split in range(len(raw) + 1):
        report = audit(capture(raw[:split], raw[split:]))
        item = report["queries"][0]
        assert item["occurrences"] == 1
        assert item["response_status"] == "observed"
        assert item["response_observation"]["first_seen_ms"] == (
            0 if split == len(raw) else 10
        )
        assert report["overview"]["unparsed_bytes"] == 0


def test_corrupt_query_or_response_and_incomplete_tail_are_not_observations():
    response = FRAMES["0x00ed"]
    bad_query = FILTER_QUERY[:-1] + bytes([FILTER_QUERY[-1] ^ 1])
    bad_response = response[:-1] + bytes([response[-1] ^ 1])
    report = audit(capture(bad_query, response))
    assert report["queries"] == []
    assert report["overview"]["unparsed_bytes"] == len(bad_query)
    report = audit(capture(FILTER_QUERY, bad_response, response[:5]))
    assert report["queries"][0]["response_status"] == "not_observed"
    assert report["overview"]["unparsed_bytes"] == len(bad_response) + 5


def test_query_bytes_inside_valid_payload_are_not_a_separate_query():
    container = frame("224000", 0xFFFF, FILTER_QUERY)
    report = audit(capture(container, FRAMES["0x00ed"]))
    assert report["queries"] == []
    assert report["overview"]["frames"] == 2
    assert report["overview"]["unparsed_bytes"] == 0
    # Compatibility: the older helper remains a byte scan of candidates.
    assert inventory(container)[0]["frame"] == FILTER_QUERY.hex()


def test_legacy_byte_inventory_keeps_counts_frames_and_checksum_status():
    bad = FILTER_QUERY[:-1] + bytes([FILTER_QUERY[-1] ^ 1])
    items = inventory(FILTER_QUERY + FILTER_QUERY + bad)
    assert {item["checksum"] for item in items} == {"match", "mismatch"}
    valid = next(item for item in items if item["checksum"] == "match")
    assert valid == {
        "dp": "0x00ED",
        "request_argument": 1,
        "frame": FILTER_QUERY.hex(),
        "checksum": "match",
        "occurrences": 2,
    }


@pytest.mark.parametrize(
    ("arguments", "expected_dp", "expected_index"),
    [
        ([], "0x00ED", None),
        (["--capture", "event"], "0x0330", -1),
        (["--capture", "event", "--event-index", "0"], "0x0160", 0),
        (["--capture", "event", "--event-index", "1"], "0x0330", 1),
    ],
)
def test_cli_manual_and_retained_event_selection(
    tmp_path, monkeypatch, arguments, expected_dp, expected_index
):
    latest_query = bytes.fromhex("108000300300000400004ef8")
    event = capture(latest_query, FRAMES["0x0330"])
    event["previous_captures"] = [capture(BYPASS_QUERY, FRAMES["0x0160"])]
    data = {
        "data": {
            "capture": capture(FILTER_QUERY, FRAMES["0x00ed"]),
            "event_capture": event,
        }
    }
    source, output = tmp_path / "source.json", tmp_path / "report.json"
    source.write_text(json.dumps(data))
    monkeypatch.setattr(
        "sys.argv", ["audit", str(source), "--output", str(output), *arguments]
    )
    main()
    result = json.loads(output.read_text())
    assert result["queries"][0]["dp"] == expected_dp
    assert result["event_index"] == expected_index
    assert result["selected_capture"] == (
        "manual" if expected_index is None else "event"
    )
    assert json.loads(source.read_text()) == data


@pytest.mark.parametrize("wrapper", ["bare", "capture"])
def test_cli_supports_bare_and_capture_wrappers(tmp_path, monkeypatch, wrapper):
    data = capture(FILTER_QUERY, FRAMES["0x00ed"])
    if wrapper == "capture":
        data = {"capture": data}
    source, output = tmp_path / "source.json", tmp_path / "report.json"
    source.write_text(json.dumps(data))
    monkeypatch.setattr("sys.argv", ["audit", str(source), "--output", str(output)])
    main()
    assert json.loads(output.read_text())["queries"][0]["response_status"] == "observed"


@pytest.mark.parametrize(
    "arguments",
    [
        ["--event-index", "0"],
        ["--event-index", "-1"],
        ["--capture", "event", "--event-index", "3"],
        ["--capture", "event", "--event-index", "-2"],
    ],
)
def test_invalid_event_selection_writes_no_output(tmp_path, monkeypatch, arguments):
    source, output = tmp_path / "source.json", tmp_path / "report.json"
    data = {"data": {"capture": capture(), "event_capture": capture()}}
    source.write_text(json.dumps(data))
    monkeypatch.setattr(
        "sys.argv", ["audit", str(source), "--output", str(output), *arguments]
    )
    with pytest.raises(SystemExit):
        main()
    assert not output.exists()
    assert json.loads(source.read_text()) == data


def test_cli_cannot_overwrite_input(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    data = {"data": {"capture": capture(FILTER_QUERY)}}
    source.write_text(json.dumps(data))
    monkeypatch.setattr("sys.argv", ["audit", str(source), "--output", str(source)])
    with pytest.raises(SystemExit):
        main()
    assert json.loads(source.read_text()) == data


@pytest.mark.parametrize("arguments", [[], ["--capture", "manual"]])
def test_cli_raw_bytes_preserve_legacy_untimed_candidate_report(
    tmp_path, monkeypatch, arguments
):
    source, output = tmp_path / "source.bin", tmp_path / "report.json"
    bad = FILTER_QUERY[:-1] + bytes([FILTER_QUERY[-1] ^ 1])
    raw = b"noise" + FILTER_QUERY + FILTER_QUERY + bad
    source.write_bytes(raw)
    monkeypatch.setattr(
        "sys.argv", ["audit", str(source), "--output", str(output), *arguments]
    )
    main()
    report = json.loads(output.read_text())
    assert report == inventory(raw)
    assert isinstance(report, list)
    assert {item["checksum"] for item in report} == {"match", "mismatch"}
    assert source.read_bytes() == raw


@pytest.mark.parametrize(
    "arguments",
    [
        ["--capture", "event"],
        ["--capture", "event", "--event-index", "0"],
        ["--event-index", "-1"],
    ],
)
def test_cli_raw_bytes_reject_event_selection(tmp_path, monkeypatch, arguments):
    source, output = tmp_path / "source.bin", tmp_path / "report.json"
    source.write_bytes(FILTER_QUERY)
    monkeypatch.setattr(
        "sys.argv", ["audit", str(source), "--output", str(output), *arguments]
    )
    with pytest.raises(SystemExit):
        main()
    assert not output.exists()
    assert source.read_bytes() == FILTER_QUERY
