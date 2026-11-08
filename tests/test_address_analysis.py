"""Candidate routing and exchange pairing remain bounded, ordered and semantic-free."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.address_analysis import analyze_exchanges, decode_header
from tools.inventory_capture import inventory


# Synthetic route variations isolate pairing rules; positive wire examples below
# retain their original checksum bytes rather than generating expected checksums.
def header(kind=0, source=1, destination=2):
    return ((destination << 14) | (source << 4) | kind).to_bytes(3, "little").hex()


def frame(kind=0, source=1, destination=2, dp=0x0194, payload=b"\x01\x00"):
    body = bytes.fromhex(header(kind, source, destination))
    body += dp.to_bytes(2, "little") + b"\0\0" + bytes([len(payload) * 2])
    body += payload
    return body + checksum(body).to_bytes(2, "little")


def report(*items, **options):
    return inventory(
        [{"elapsed_ms": time, "hex": data.hex()} for time, data in items],
        include_frame_observations=True,
        **options,
    )


def assert_accounting(result):
    counts = result["counts"]
    known = sum(counts[key] for key in ("query", "set", "response", "confirm"))
    assert known == 2 * counts["pairs"] + counts["unmatched"]
    assert counts["pairs"] == len(result["pairs"])
    assert counts["unmatched"] == len(result["unmatched"])
    assert counts["unknown"] == len(result["unknown_frames"])
    assert counts["frames"] == known + counts["unknown"]
    indexes = [
        item[side]["frame_index"]
        for item in result["pairs"]
        for side in ("request", "reply")
    ] + [item["frame"]["frame_index"] for item in result["unmatched"]]
    indexes += [item["frame_index"] for item in result["unknown_frames"]]
    assert len(indexes) == len(set(indexes)) == counts["frames"]


@pytest.mark.parametrize(
    ("raw", "kind", "source", "destination"),
    [
        ("108000", 0, 1, 2),
        ("224000", 2, 2, 1),
        ("118007", 1, 1, 30),
        ("e34100", 3, 30, 1),
        ("10000a", 0, 1, 40),
    ],
)
def test_known_headers_decode_candidate_fields_only(raw, kind, source, destination):
    value = decode_header(raw)
    assert value == {
        "header_le24": int.from_bytes(bytes.fromhex(raw), "little"),
        "type": kind,
        "type_name": ("query", "set", "response", "confirm")[kind],
        "source": source,
        "destination": destination,
    }
    assert decode_header(raw.upper()) == value


@pytest.mark.parametrize("source", [0, 1, 1023])
@pytest.mark.parametrize("destination", [0, 1, 1023])
@pytest.mark.parametrize("kind", [0, 3, 4, 15])
def test_bit_field_boundaries_and_unknown_types(source, destination, kind):
    value = decode_header(header(kind, source, destination))
    assert (value["type"], value["source"], value["destination"]) == (
        kind,
        source,
        destination,
    )
    if kind > 3:
        assert value["type_name"] == "unknown"


@pytest.mark.parametrize(
    "raw",
    [
        None,
        True,
        0x108000,
        b"\x10\x80\x00",
        "",
        "1080",
        "10800000",
        "gg8000",
        "10 80 00",
    ],
)
def test_malformed_header_rejected(raw):
    with pytest.raises(ValueError):
        decode_header(raw)


def test_original_node30_query_and_set_pairs_keep_wire_checksums():
    chunks = json.loads(
        (Path(__file__).parent / "fixtures/address_frames.json").read_text()
    )
    for row in chunks:
        raw = bytes.fromhex(row["hex"])
        assert checksum(raw[:-2]) == int.from_bytes(raw[-2:], "little")
    source = inventory(chunks, include_frame_observations=True)
    original = deepcopy(source)
    result = analyze_exchanges(source)
    assert_accounting(result)
    assert source == original
    assert [item["kind"] for item in result["pairs"]] == [
        "set_confirm",
        "query_response",
    ]
    assert [item["delta_ms"] for item in result["pairs"]] == [8, 9]
    assert result["pairs"][0]["reply"]["payload_hex"] == ""
    assert result["pairs"][1]["reply"]["payload_hex"] == "0500"
    assert all(item["classification"] == "candidate" for item in result["pairs"])
    assert result["participants"] == [
        {"address": 1, "sent": 2, "received": 2},
        {"address": 30, "sent": 2, "received": 2},
    ]
    assert [(r["source"], r["destination"], r["count"]) for r in result["routes"]] == [
        (1, 30, 2),
        (30, 1, 2),
    ]
    assert not any(
        word in json.dumps(result).lower()
        for word in ("ptc-modul", "t300", "heater_on")
    )


def test_interleaved_same_dp_routes_and_directions_are_independent():
    source = report(
        (0, frame()),
        (10, frame(destination=30)),
        (20, frame(source=2, destination=1)),
        (30, frame(2, 2, 1, payload=b"abcd")),
        (40, frame(2, 30, 1, payload=b"x")),
        (50, frame(2, 1, 2, payload=b"")),
    )
    result = analyze_exchanges(source)
    assert_accounting(result)
    assert [
        (p["request"]["frame_index"], p["reply"]["frame_index"])
        for p in result["pairs"]
    ] == [
        (0, 3),
        (1, 4),
        (2, 5),
    ]
    assert result["unmatched"] == []
    assert result["pairs"][0]["request"]["payload_bytes"] == 2
    assert result["pairs"][0]["reply"]["payload_bytes"] == 4


def test_wrong_reply_dp_endpoints_and_type_do_not_consume_request():
    result = analyze_exchanges(
        report(
            (0, frame()),
            (10, frame(2, 2, 1, dp=0x0195)),
            (20, frame(2, 1, 2)),
            (30, frame(3, 2, 1, payload=b"")),
            (40, frame(2, 2, 1)),
        )
    )
    assert_accounting(result)
    assert [
        (p["request"]["frame_index"], p["reply"]["frame_index"])
        for p in result["pairs"]
    ] == [(0, 4)]
    assert {item["reason"] for item in result["unmatched"]} == {
        "wrong_data_point",
        "wrong_endpoints",
        "wrong_reply_type",
    }


def test_unknown_frame_retained_without_breaking_other_route():
    result = analyze_exchanges(
        report((0, frame()), (5, frame(15)), (10, frame(2, 2, 1)))
    )
    assert_accounting(result)
    assert result["counts"]["pairs"] == 1
    unknown = result["unknown_frames"][0]
    assert unknown["address"]["type"] == 15
    assert unknown["address"]["type_name"] == "unknown"


def test_simultaneous_tcp_completion_keeps_wire_order_and_timing_ambiguity():
    result = analyze_exchanges(
        report((20, frame() + frame(2, 2, 1))), max_response_ms=0
    )
    assert_accounting(result)
    pair = result["pairs"][0]
    assert (pair["request"]["frame_index"], pair["reply"]["frame_index"]) == (0, 1)
    assert pair["delta_ms"] == 0
    assert pair["same_tcp_timestamp"] is True
    reversed_order = analyze_exchanges(report((20, frame(2, 2, 1) + frame())))
    assert_accounting(reversed_order)
    assert reversed_order["pairs"] == []


@pytest.mark.parametrize(("delay", "paired"), [(0, True), (1000, True), (1001, False)])
def test_response_deadline_is_inclusive(delay, paired):
    result = analyze_exchanges(report((0, frame()), (delay, frame(2, 2, 1))))
    assert_accounting(result)
    assert bool(result["pairs"]) is paired
    if not paired:
        assert {row["reason"] for row in result["unmatched"]} == {
            "timeout",
            "late_reply",
        }


def test_repeated_overlapping_requests_quarantine_key_instead_of_latest_wins():
    result = analyze_exchanges(
        report(
            (0, frame()),
            (10, frame(payload=b"\x02\0")),
            (20, frame(2, 2, 1)),
            (1010, frame(2, 2, 1)),
            (1011, frame()),
            (1012, frame(2, 2, 1)),
        )
    )
    assert_accounting(result)
    assert [
        (p["request"]["frame_index"], p["reply"]["frame_index"])
        for p in result["pairs"]
    ] == [(4, 5)]
    assert [row["reason"] for row in result["unmatched"]].count(
        "overlapping_request"
    ) == 2
    assert [row["reason"] for row in result["unmatched"]].count("ambiguous_reply") == 2


def test_third_overlapping_request_extends_quarantine_only_for_its_key():
    result = analyze_exchanges(
        report(
            (0, frame()),
            (10, frame()),
            (900, frame()),
            (901, frame(destination=30)),
            (902, frame(2, 30, 1)),
            (1011, frame(2, 2, 1)),
            (1901, frame()),
            (1902, frame(2, 2, 1)),
        )
    )
    assert_accounting(result)
    assert [
        (p["request"]["frame_index"], p["reply"]["frame_index"])
        for p in result["pairs"]
    ] == [(3, 4), (6, 7)]
    assert any(
        row["reason"] == "ambiguous_reply" and row["frame"]["frame_index"] == 5
        for row in result["unmatched"]
    )


@pytest.mark.parametrize("loss", ["noise", "corruption", "index_jump"])
def test_loss_between_request_and_response_prevents_pairing(loss):
    middle = b"noise" if loss == "noise" else b""
    if loss == "corruption":
        valid = frame(2, 2, 1)
        middle = valid[:-1] + bytes([valid[-1] ^ 1])
    source = report((0, frame()), (10, middle), (20, frame(2, 2, 1)))
    if loss == "index_jump":
        source["frame_observations"][1]["frame_index"] = 2
    result = analyze_exchanges(source)
    assert_accounting(result)
    assert result["pairs"] == []
    assert result["continuity_breaks"]
    assert any(item["reason"] == "continuity_break" for item in result["unmatched"])


def test_continuity_loss_cannot_be_hidden_by_new_request_on_pending_key():
    result = analyze_exchanges(
        report((0, frame()), (10, b"noise" + frame()), (20, frame(2, 2, 1)))
    )
    assert_accounting(result)
    assert result["pairs"] == []


def test_orphans_duplicates_and_empty_set_confirm_never_imply_effect():
    result = analyze_exchanges(
        report(
            (0, frame(3, 2, 1, payload=b"")),
            (10, frame(1)),
            (20, frame(3, 2, 1, payload=b"")),
            (30, frame(3, 2, 1, payload=b"")),
        )
    )
    assert_accounting(result)
    assert result["pairs"][0]["kind"] == "set_confirm"
    assert result["pairs"][0]["classification"] == "candidate"
    assert {row["reason"] for row in result["unmatched"]} == {
        "orphan_reply",
        "duplicate_reply",
    }


def test_separate_windows_are_independent_and_selected_end_is_exclusive():
    items = ((0, frame()), (10, frame(2, 2, 1)))
    before = analyze_exchanges(report(*items, end_ms=10))
    after = analyze_exchanges(report(*items, start_ms=10, end_ms=20))
    for result in (before, after):
        assert_accounting(result)
        assert result["pairs"] == []
    assert before["unmatched"][0]["reason"] == "end_of_window"
    assert after["unmatched"][0]["reason"] == "orphan_reply"
    assert analyze_exchanges(report())["pairs"] == []


@pytest.mark.parametrize("maximum", [True, -1, 1.0, "1000", None])
def test_invalid_response_limit_rejected(maximum):
    with pytest.raises(ValueError):
        analyze_exchanges(report(), max_response_ms=maximum)


@pytest.mark.parametrize(
    "change",
    [
        "payload",
        "time",
        "index",
        "unparsed",
        "outside_window",
        "outside_capture",
        "identity",
    ],
)
def test_malformed_inventory_observations_rejected(change):
    source = report((10, frame()), (20, frame(2, 2, 1)))
    rows = source["frame_observations"]
    if change == "payload":
        rows[0]["payload_hex"] = "00"
    elif change == "time":
        rows[1]["elapsed_ms"] = 9
    elif change == "index":
        rows[1]["frame_index"] = rows[0]["frame_index"]
    elif change == "unparsed":
        rows[0]["unparsed_bytes_before"] = 5
    elif change == "outside_window":
        source["window"]["start_ms"] = 11
    elif change == "outside_capture":
        source["last_chunk_ms"] = 19
    else:
        rows[0]["identity"] = "invalid"
    with pytest.raises(ValueError):
        analyze_exchanges(source)


@pytest.mark.parametrize(
    "source",
    [None, [], {}, {"window": {"start_ms": 0, "end_ms": None}, "last_chunk_ms": 0}],
)
def test_missing_original_observation_stream_is_rejected(source):
    with pytest.raises(ValueError):
        analyze_exchanges(source)
