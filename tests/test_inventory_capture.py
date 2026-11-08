"""Full inventory must retain unknown identities and visible coverage gaps."""

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.inventory_capture import inventory

OFF = bytes.fromhex("118000f80100000800000000a1fd")
ON = bytes.fromhex("118000f8010000084000000030b0")
ACK = bytes.fromhex("234000f801000000ebe4")


def chunk(data, time=0):
    return {"hex": data.hex(), "elapsed_ms": time}


def test_changes_repeats_and_each_stream_split():
    data = OFF + ON + ON + ACK + OFF
    expected = inventory([chunk(data, 42)])
    for split in range(len(data) + 1):
        assert inventory([chunk(data[:split], 42), chunk(data[split:], 42)]) == expected
    group = expected["groups"]["118000/0x01F8/4"]
    assert group["count"] == 4
    assert [c["payload_hex"] for c in group["changes"]] == [
        "00000000",
        "40000000",
        "00000000",
    ]
    assert expected["frames"] == 5
    assert expected["unparsed_bytes"] == 0


def test_unknown_identity_is_separate_and_timestamp_is_frame_completion():
    body = bytes.fromhex("998009f80100000840000000")
    unknown = body + checksum(body).to_bytes(2, "little")
    result = inventory([chunk(OFF + unknown[:5], 10), chunk(unknown[5:], 20)])
    assert set(result["groups"]) == {"118000/0x01F8/4", "998009/0x01F8/4"}
    assert result["groups"]["998009/0x01F8/4"]["changes"][0]["elapsed_ms"] == 20


def test_noise_corruption_and_incomplete_tail_reported():
    corrupt = ON[:-1] + bytes([ON[-1] ^ 1])
    result = inventory([chunk(b"noise" + corrupt + OFF + ON[:6])])
    assert result["frames"] == 1
    assert result["unparsed_bytes"] == 5 + len(corrupt) + 6


def test_empty_and_invalid_timing():
    assert inventory([])["frames"] == 0
    with pytest.raises(ValueError, match="monotonic"):
        inventory([chunk(OFF, 2), chunk(ON, 1)])
    with pytest.raises(ValueError, match="nonnegative"):
        inventory([chunk(OFF, True)])


def test_optional_ordered_observations_keep_size_changes_and_skipped_bytes():
    body = bytes.fromhex("118000f8010000044000")
    short = body + checksum(body).to_bytes(2, "little")
    result = inventory(
        [chunk(OFF + short + b"noise" + ON, 42)],
        include_frame_observations=True,
    )
    rows = result["frame_observations"]
    assert [row["identity"] for row in rows] == [
        "118000/0x01F8/4",
        "118000/0x01F8/2",
        "118000/0x01F8/4",
    ]
    assert [row["frame_index"] for row in rows] == [0, 1, 2]
    assert [row["unparsed_bytes_before"] for row in rows] == [0, 0, 5]
    assert [row["elapsed_ms"] for row in rows] == [42, 42, 42]
    assert "frame_observations" not in inventory([chunk(OFF)])


def test_observation_windows_retain_global_wire_order_and_frame_completion():
    result = inventory(
        [chunk(OFF + ON[:4], 0), chunk(ON[4:], 10), chunk(OFF, 20)],
        start_ms=10,
        end_ms=20,
        include_frame_observations=True,
    )
    assert result["frame_observations"] == [
        {
            "identity": "118000/0x01F8/4",
            "elapsed_ms": 10,
            "frame_index": 1,
            "payload_hex": "40000000",
            "unparsed_bytes_before": 0,
        }
    ]
    with pytest.raises(ValueError, match="boolean"):
        inventory([], include_frame_observations=1)


def test_candidate_addresses_enrich_groups_without_mutating_observation_rows():
    chunks = [chunk(OFF + ACK, 10)]
    original = [dict(row) for row in chunks]
    result = inventory(chunks, include_frame_observations=True)
    assert chunks == original
    group = result["groups"]["118000/0x01F8/4"]
    assert group["address"] == {
        "header_le24": 0x008011,
        "type": 1,
        "type_name": "set",
        "source": 1,
        "destination": 2,
    }
    assert result["frame_observations"][0] == {
        "identity": "118000/0x01F8/4",
        "elapsed_ms": 10,
        "frame_index": 0,
        "payload_hex": "00000000",
        "unparsed_bytes_before": 0,
    }
    assert set(result["frame_observations"][1]) == {
        "identity",
        "elapsed_ms",
        "frame_index",
        "payload_hex",
        "unparsed_bytes_before",
    }


def test_same_dp_other_address_and_unknown_type_keep_distinct_groups():
    def checked(raw):
        body = bytes.fromhex(raw)
        return body + checksum(body).to_bytes(2, "little")

    other_address = checked("118007f80100000800000000")
    unknown_type = checked("1f8007f80100000800000000")
    result = inventory([chunk(OFF + other_address + unknown_type)])
    assert len(result["groups"]) == 3
    assert result["groups"]["118000/0x01F8/4"]["address"]["destination"] == 2
    assert result["groups"]["118007/0x01F8/4"]["address"]["destination"] == 30
    unknown = result["groups"]["1f8007/0x01F8/4"]["address"]
    assert unknown["type"] == 15
    assert unknown["type_name"] == "unknown"
    assert result["frames"] == 3
