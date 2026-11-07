"""SET summaries preserve identity, continuity boundaries and point references."""

import copy

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.inventory_capture import inventory
from tools.set_comparison import analyze_sets, changed_bits


def frame(header="118000", dp=0x1234, payload=b"\0"):
    body = bytes.fromhex(header) + dp.to_bytes(2, "little")
    body += b"\0\0" + bytes([len(payload) * 2]) + payload
    return body + checksum(body).to_bytes(2, "little")


def row(time, payload, *, header="118000", dp=0x1234, index=0, unparsed=0):
    return {
        "identity": f"{header}/0x{dp:04X}/{len(bytes.fromhex(payload))}",
        "elapsed_ms": time,
        "frame_index": index,
        "payload_hex": payload,
        "unparsed_bytes_before": unparsed,
    }


def report(*rows, start=0, end=None, last=None):
    return {
        "window": {"start_ms": start, "end_ms": end},
        "last_chunk_ms": max((r["elapsed_ms"] for r in rows), default=0)
        if last is None
        else last,
        "frame_observations": list(rows),
    }


KEY = "118000/0x1234/1"


def counts(group):
    return [group[key] for key in ("total", "repeats", "transitions", "baselines")]


def test_low_nibble_includes_other_first_bytes_and_unknown_points_not_ack():
    rows = [
        row(0, "00", header=header, dp=0xFFFF, index=index)
        for index, header in enumerate(
            ("118000", "218001", "f18004", "019900", "118007")
        )
    ]
    rows.append(row(0, "", header="234000", dp=0xFFFF, index=len(rows)))
    result = analyze_sets(report(*rows))
    assert len(result["groups"]) == 5
    assert "234000/0xFFFF/0" not in result["groups"]
    assert all(group["baselines"] == 1 for group in result["groups"].values())
    assert "candidate" in result["classification"]
    assert "BDE origin" in result["caution"]


def test_repeats_have_no_false_transition_and_bracket_uses_last_old_sample():
    source = report(
        row(0, "00", index=0),
        row(3, "00", index=1),
        row(5, "81", index=2),
        row(6, "81", index=3),
        row(8, "00", index=4),
    )
    original = copy.deepcopy(source)
    group = analyze_sets(source)["groups"][KEY]
    assert counts(group) == [5, 2, 2, 1]
    assert [run["samples"] for run in group["runs"]] == [2, 2, 1]
    change = group["runs"][1]
    assert change["transition_bracket"] == {
        "last_old_ms": 3,
        "first_new_ms": 5,
        "last_old_frame_index": 1,
        "first_new_frame_index": 2,
    }
    assert change["changed_bits"] == [
        {"byte": 0, "bit": 0, "before": 0, "after": 1},
        {"byte": 0, "bit": 7, "before": 0, "after": 1},
    ]
    assert group["runs"][0]["previous_payload_hex"] is None
    assert source == original


def test_gap_at_threshold_and_unparsed_bytes_reset_even_identical_values():
    source = report(
        row(0, "00", index=0),
        row(10, "00", index=1),
        row(11, "00", index=2, unparsed=3),
        row(21, "01", index=3, unparsed=5),
        row(22, "01", index=4, unparsed=5),
    )
    group = analyze_sets(source, max_gap_ms=10)["groups"][KEY]
    assert counts(group) == [5, 1, 0, 4]
    assert [run["reasons"] for run in group["runs"]] == [
        ["first_observation"],
        ["gap"],
        ["unparsed_bytes"],
        ["gap", "unparsed_bytes"],
    ]
    assert all(run["transition_bracket"] is None for run in group["runs"])


def test_length_a_b_a_never_compares_across_intervening_shape():
    source = report(
        row(0, "00", index=0),
        row(1, "0000", index=1),
        row(2, "01", index=2),
        row(3, "03", index=3),
    )
    result = analyze_sets(source, data_points=[0x1234])
    assert counts(result["groups"][KEY]) == [3, 0, 1, 2]
    assert counts(result["groups"]["118000/0x1234/2"]) == [1, 0, 0, 1]
    runs = result["groups"][KEY]["runs"]
    assert runs[1]["reasons"] == ["payload_length_change"]
    assert runs[1]["changed_bits"] is None
    assert runs[2]["previous_payload_hex"] == "01"
    assert changed_bits("00", "0000") is None


def test_same_dp_other_headers_are_independent_and_filters_keep_unknown_dp():
    source = report(
        row(0, "00", index=0),
        row(1, "ff", header="118007", index=1),
        row(2, "01", index=2),
        row(3, "ff", dp=0xFFFF, index=3),
    )
    result = analyze_sets(source, data_points=(point for point in (0x1234,)))
    assert set(result["groups"]) == {KEY, "118007/0x1234/1"}
    assert counts(result["groups"][KEY]) == [2, 0, 1, 1]
    assert (
        analyze_sets(source, data_points=[0xFFFF])["groups"]["118000/0xFFFF/1"]["total"]
        == 1
    )
    assert analyze_sets(source, data_points=[])["groups"] == {}


def test_same_millisecond_uses_global_wire_order_without_inventing_latency():
    result = analyze_sets(report(row(5, "00", index=4), row(5, "01", index=6)))
    bracket = result["groups"][KEY]["runs"][1]["transition_bracket"]
    assert bracket["last_old_ms"] == bracket["first_new_ms"] == 5
    assert bracket["last_old_frame_index"] == 4
    assert bracket["first_new_frame_index"] == 6
    assert "not wire latency" in result["caution"]


def test_reference_matches_actual_photo_time_not_trigger_and_is_only_a_point():
    source = report(row(0, "00", index=0), row(10, "01", index=1), last=20)
    observations = [
        {
            "elapsed_ms": 12,
            "label": "BDE photo",
            "observation": "Visible text",
            "trigger_elapsed_ms": 0,
            "evidence_id": "private-photo-1",
        }
    ]
    original = copy.deepcopy(observations)
    result = analyze_sets(source, observations=observations, observation_window_ms=2)
    point = result["observations"][0]
    assert point["status"] == "context_only"
    assert point["trigger_elapsed_ms"] == 0
    assert point["nearby_changes"][0]["delta_ms"] == -2
    assert point["nearby_changes"][0]["elapsed_ms"] == 10
    assert observations == original
    assert "interval" not in point
    assert not analyze_sets(
        source,
        observations=[{**observations[0], "elapsed_ms": 0}],
        observation_window_ms=2,
    )["observations"][0]["nearby_changes"]


def test_photos_outside_window_or_capture_cannot_be_associated():
    source = report(
        row(10, "00", index=1), row(12, "01", index=2), start=10, end=20, last=30
    )
    result = analyze_sets(
        source,
        observation_window_ms=100,
        observations=[
            {"elapsed_ms": time, "label": "Photo", "observation": "State"}
            for time in (9, 20, 31, 12)
        ],
    )
    assert [point["status"] for point in result["observations"]] == [
        "outside_window",
        "outside_window",
        "outside_capture",
        "context_only",
    ]
    assert all(not point["nearby_changes"] for point in result["observations"][:3])
    assert all(not point["nearby_samples"] for point in result["observations"][:3])
    assert len(result["observations"][3]["nearby_changes"]) == 1


def test_stable_samples_around_photo_use_photo_time_and_remain_observations():
    source = report(
        row(0, "ff", index=0),
        row(9, "00", index=1),
        row(11, "00", index=2),
        row(13, "00", index=3),
    )
    result = analyze_sets(
        source,
        observation_window_ms=2,
        observations=[
            {
                "elapsed_ms": 10,
                "trigger_elapsed_ms": 0,
                "label": "PTC photo",
                "observation": "On",
            }
        ],
    )
    point = result["observations"][0]
    assert [r["payload_hex"] for r in point["nearby_samples"]] == ["00", "00"]
    assert [r["delta_ms"] for r in point["nearby_samples"]] == [-1, 1]
    assert [r["relation"] for r in point["nearby_samples"]] == ["before", "after"]
    assert all(r["payload_hex"] != "ff" for r in point["nearby_samples"])
    assert point["status"] == "context_only"


def test_same_time_photo_samples_keep_first_last_wire_rows_and_mark_ambiguity():
    source = report(
        row(5, "00", index=1),
        row(5, "01", index=2),
        row(5, "03", index=3),
    )
    point = analyze_sets(
        source,
        observations=[
            {
                "elapsed_ms": 5,
                "label": "Photo",
                "observation": "Visible state",
            }
        ],
    )["observations"][0]
    assert len(point["nearby_samples"]) == 2
    assert [r["frame_index"] for r in point["nearby_samples"]] == [1, 3]
    assert all(r["relation"] == "at" for r in point["nearby_samples"])
    assert all(r["same_timestamp_order_ambiguous"] for r in point["nearby_samples"])


def test_empty_capture_and_first_frame_are_not_transitions():
    assert analyze_sets(report())["groups"] == {}
    group = analyze_sets(report(row(3, "01")))["groups"][KEY]
    assert counts(group) == [1, 0, 0, 1]
    assert group["runs"][0]["changed_bits"] is None


def test_inventory_chunk_splits_use_one_parser_and_completion_timing():
    data = (
        frame(payload=b"\0")
        + frame(header="234000", payload=b"")
        + frame(payload=b"\1")
    )
    expected = None
    for split in range(len(data) + 1):
        chunks = [
            {"elapsed_ms": 7, "hex": data[:split].hex()},
            {"elapsed_ms": 7, "hex": data[split:].hex()},
        ]
        result = analyze_sets(inventory(chunks, include_frame_observations=True))
        if expected is None:
            expected = result
        assert result == expected
    assert counts(expected["groups"][KEY]) == [2, 0, 1, 1]
    partial = frame(payload=b"\0")
    chunks = [
        {"elapsed_ms": 1, "hex": partial[:5].hex()},
        {"elapsed_ms": 9, "hex": partial[5:].hex()},
    ]
    assert (
        analyze_sets(inventory(chunks, include_frame_observations=True))["groups"][KEY][
            "runs"
        ][0]["first_seen_ms"]
        == 9
    )


def test_inventory_corruption_and_incomplete_tail_are_not_state_changes():
    old, new = frame(payload=b"\0"), frame(payload=b"\1")
    corrupt = new[:-1] + bytes([new[-1] ^ 1])
    data = old + corrupt + new + old[:6]
    inv = inventory(
        [{"elapsed_ms": 7, "hex": data.hex()}], include_frame_observations=True
    )
    result = analyze_sets(inv)
    assert counts(result["groups"][KEY]) == [2, 0, 0, 2]
    assert result["groups"][KEY]["runs"][1]["reasons"] == ["unparsed_bytes"]
    assert inv["unparsed_bytes"] == len(corrupt) + 6


@pytest.mark.parametrize(
    "options",
    [
        {"max_gap_ms": True},
        {"max_gap_ms": 0},
        {"max_gap_ms": float("nan")},
        {"observation_window_ms": False},
        {"observation_window_ms": -1},
        {"observation_window_ms": float("inf")},
        {"data_points": [True]},
        {"data_points": [-1]},
        {"data_points": [65536]},
        {"data_points": 4},
        {"data_points": [float("nan")]},
        {"observations": {}},
        {"observations": [{"elapsed_ms": True, "label": "x", "observation": "y"}]},
        {
            "observations": [
                {
                    "elapsed_ms": 0,
                    "label": "x",
                    "observation": "y",
                    "trigger_elapsed_ms": False,
                }
            ]
        },
        {
            "observations": [
                {"elapsed_ms": 0, "label": "x", "observation": "y", "confirmed": True}
            ]
        },
        {"observations": [{"elapsed_ms": 0, "label": "x", "observation": "\n"}]},
        {
            "observations": [
                {
                    "elapsed_ms": 0,
                    "label": "x",
                    "observation": "y",
                    "evidence_id": "x" * 129,
                }
            ]
        },
    ],
)
def test_invalid_parameters_and_points_are_rejected(options):
    with pytest.raises(ValueError):
        analyze_sets(report(), **options)


@pytest.mark.parametrize(
    "field,value",
    [
        ("elapsed_ms", True),
        ("frame_index", False),
        ("unparsed_bytes_before", -1),
        ("payload_hex", "0"),
        ("payload_hex", "00 00"),
        ("identity", "118000/0x1234/2"),
        ("identity", "118000/0xZZZZ/1"),
    ],
)
def test_invalid_frame_metadata_is_rejected(field, value):
    sample = {**row(0, "00"), field: value}
    with pytest.raises(ValueError):
        analyze_sets(report(sample))


@pytest.mark.parametrize(
    "rows",
    [
        [row(1, "00", index=0), row(0, "01", index=1)],
        [row(0, "00", index=1), row(1, "01", index=1)],
        [row(0, "00", index=0, unparsed=1), row(1, "01", index=1)],
    ],
)
def test_unsorted_wire_order_is_rejected(rows):
    with pytest.raises(ValueError, match="wire order"):
        analyze_sets(report(*rows, last=2))


def test_missing_inventory_details_and_invalid_windows_are_rejected():
    with pytest.raises(ValueError, match="include_frame_observations"):
        analyze_sets({"window": {"start_ms": 0, "end_ms": None}, "last_chunk_ms": 0})
    with pytest.raises(ValueError):
        analyze_sets(report(start=True))
    with pytest.raises(ValueError):
        analyze_sets(report(start=2, end=2))
    with pytest.raises(ValueError, match="selected window"):
        analyze_sets(report(row(0, "00"), start=1))
