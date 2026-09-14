"""Recorded ACKs establish temporal association, not applied actuator state."""

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.audit_panel_writes import audit

ON = bytes.fromhex("118000f8010000084000000030b0")
OFF = bytes.fromhex("118000f80100000800000000a1fd")
ACK = bytes.fromhex("234000f801000000ebe4")
TARGET = bytes.fromhex("11800027020000080000a84152d0")
TARGET_ACK = bytes.fromhex("234000270200000039a1")


def chunks(*entries):
    return [{"elapsed_ms": time, "hex": frame.hex()} for time, frame in entries]


def point(result):
    return result["points"]["0x01F8"]


def alter(frame, index, value):
    body = bytearray(frame[:-2])
    body[index] = value
    return bytes(body) + checksum(body).to_bytes(2, "little")


def test_recorded_sequence_and_repeat_vs_change():
    result = audit(
        chunks(
            (0, OFF),
            (18, ACK),
            (5000, ON),
            (5018, ACK),
            (10000, ON),
            (10018, ACK),
            (15000, OFF),
            (15018, ACK),
        )
    )
    p = point(result)
    assert result["unparsed_bytes"] == 0
    assert p["sets"] == p["ack_associations"] == 4
    assert p["value_changes"] == 2
    assert p["unchanged_repeats"] == 1
    assert [c["value"] for c in p["changes"]] == [0, 64, 0]
    assert p["ack_capture_delta_ms"] == {"min": 18, "max": 18}
    assert p["set_interval_ms"] == {"min": 5000, "max": 5000}
    assert p["unchanged_set_interval_ms"] == {
        "count": 1,
        "min": 5000,
        "median": 5000,
        "max": 5000,
    }


def test_repeat_timing_excludes_changes_and_other_data_points():
    result = audit(
        chunks(
            (0, OFF),
            (10, ACK),
            (5000, OFF),
            (5010, ACK),
            (5200, ON),
            (5210, ACK),
            (8000, TARGET),
            (8010, TARGET_ACK),
            (10400, ON),
            (10410, ACK),
            (11000, OFF),
            (11010, ACK),
        )
    )
    assert point(result)["unchanged_set_interval_ms"] == {
        "count": 2,
        "min": 5000,
        "median": 5100,
        "max": 5200,
    }
    assert result["points"]["0x0227"]["unchanged_set_interval_ms"] is None
    assert (
        point(audit(chunks((0, OFF), (10, ACK))))["unchanged_set_interval_ms"] is None
    )


def test_each_chunk_split_preserves_frames():
    data = ON + ACK + TARGET + TARGET_ACK
    expected = audit(chunks((42, data)))
    for split in range(1, len(data)):
        assert audit(chunks((42, data[:split]), (42, data[split:]))) == expected
    assert point(expected)["ack_capture_delta_ms"] == {"min": 0, "max": 0}


def test_interleaved_dps_and_exact_ack_identity():
    result = audit(
        chunks(
            (0, ON + TARGET),
            (10, alter(ACK, 0, 0x22) + alter(ACK, 1, 0x41)),
            (20, TARGET_ACK),
            (30, ACK),
        )
    )
    assert point(result)["ack_associations"] == 1
    assert point(result)["ack_capture_delta_ms"] == {"min": 30, "max": 30}
    assert result["points"]["0x0227"]["ack_capture_delta_ms"]["max"] == 20


def test_overlapping_sets_do_not_get_falsely_unique_ack():
    p = point(audit(chunks((0, ON), (100, OFF), (110, ACK), (120, ACK))))
    assert p["ack_associations"] == 0
    assert p["ambiguous_acks"] == 1
    assert p["sets_with_ambiguous_ack"] == 2
    assert p["acks_without_pending_set"] == 1


def test_late_ack_and_truncated_observation_window():
    p = point(audit(chunks((0, ON), (1001, ACK), (2000, OFF))))
    assert p["sets_without_ack_in_window"] == 1
    assert p["acks_without_pending_set"] == 1
    assert p["sets_pending_at_capture_end"] == 1
    p = point(audit(chunks((0, ON), (1001, TARGET))))
    assert p["sets_without_ack_in_window"] == 1
    assert p["sets_pending_at_capture_end"] == 0


def test_corruption_unknown_bytes_and_truncated_tail_are_visible():
    corrupt = ON[:-1] + bytes([ON[-1] ^ 1])
    result = audit(chunks((0, b"noise" + corrupt + ON + ACK + OFF[:7])))
    assert result["unparsed_bytes"] == 5 + len(corrupt) + 7
    assert point(result)["sets"] == point(result)["ack_associations"] == 1


def test_wrong_set_size_and_other_node_are_not_control_values():
    wrong_size = alter(TARGET, 3, 0xE1)  # DP 0x02E1: not selected
    other_node = alter(ON, 2, 7)
    result = audit(chunks((0, wrong_size + other_node)))
    assert result["points"] == {}
    body = bytes.fromhex("118000f8010000044000")
    result = audit(chunks((0, body + checksum(body).to_bytes(2, "little"))))
    assert result["malformed_selected_sets"] == 1
    assert result["points"] == {}


def test_invalid_timing_and_empty_capture():
    with pytest.raises(ValueError, match="monotonic"):
        audit(chunks((10, ON), (0, ACK)))
    with pytest.raises(ValueError, match="positive"):
        audit([], 0)
    assert audit([])["bytes"] == 0
    assert audit([])["points"] == {}


def test_corrupt_and_nonempty_ack_do_not_confirm_set():
    corrupt = ACK[:-1] + bytes([ACK[-1] ^ 1])
    body = bytes.fromhex("234000f8010000040000")
    nonempty = body + checksum(body).to_bytes(2, "little")
    result = audit(chunks((0, ON), (20, corrupt + nonempty), (1100, TARGET)))
    assert point(result)["ack_associations"] == 0
    assert point(result)["sets_without_ack_in_window"] == 1
    assert result["unparsed_bytes"] == len(corrupt)
