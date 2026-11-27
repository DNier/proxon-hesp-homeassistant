"""Selected original controller replies establish bytes, not new parameter roles."""

import json
import struct
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import RESPONSE_POINTS, Decoder
from tools.inventory_capture import inventory

REPLIES = json.loads(
    (Path(__file__).parent / "fixtures/controller_catalog_frames.json").read_text()
)


@pytest.mark.parametrize("point,recorded", REPLIES.items())
def test_original_controller_reply_has_complete_payload_and_valid_checksum(
    point, recorded
):
    raw = bytes.fromhex(recorded)
    assert raw[:3] == bytes.fromhex("224000")
    assert int.from_bytes(raw[3:7], "little") == int(point, 16)
    assert raw[7] == 2 * (len(raw) - 10)
    assert checksum(raw[:-2]) == int.from_bytes(raw[-2:], "little")
    result = inventory([{"elapsed_ms": 0, "hex": recorded}])
    assert result["frames"] == 1
    assert result["unparsed_bytes"] == 0


@pytest.mark.parametrize(
    "point,expected",
    [
        ("0124", [float(value) for value in range(15, -5, -1)]),
        ("0125", [-2.0] * 12 + [-3.0, -4.0, -4.0, -5.0, -6.0, -6.0, -7.0, -7.0]),
    ],
)
def test_untruncated_arrays_contain_twenty_original_float32_values(point, expected):
    raw = bytes.fromhex(REPLIES[point])
    assert len(raw[8:-2]) == 80
    assert list(struct.unpack("<20f", raw[8:-2])) == expected
    assert int(point, 16) not in RESPONSE_POINTS
    decoder = Decoder()
    assert decoder.feed(raw) == []
    assert decoder.stats.accepted == 0


def test_same_numbered_controller_0191_remains_distinct_from_panel_address_30():
    raw = bytes.fromhex(REPLIES["0191"])
    assert raw[:3] == bytes.fromhex("224000")
    assert len(raw[8:-2]) == 4
    assert struct.unpack("<f", raw[8:-2])[0] == -30.0
    assert Decoder().feed(raw) == []


def test_recorded_0232_byte_does_not_establish_heat_demand():
    raw = bytes.fromhex(REPLIES["0232"])
    assert raw[8:-2] == bytes.fromhex("01")
    assert 0x0232 not in RESPONSE_POINTS
    decoder = Decoder()
    assert decoder.feed(raw) == []
    assert decoder.stats.accepted == 0


@pytest.mark.parametrize(
    "point,expected",
    [
        ("0104", (115.0, 125.0)),
        ("015F", (12.0,)),
        ("0195", (112.16560363769531,)),
    ],
)
def test_original_candidate_values_remain_unmapped(point, expected):
    raw = bytes.fromhex(REPLIES[point])
    assert struct.unpack("<" + "f" * len(expected), raw[8:-2]) == expected
    assert int(point, 16) not in RESPONSE_POINTS
    decoder = Decoder()
    assert decoder.feed(raw) == []
    assert decoder.stats.accepted == 0


@pytest.mark.parametrize(
    "point,key,expected",
    [
        ("0115", "heat_pump_start_threshold", 0.399993896484375),
        ("011C", "heat_pump_continuous_run_threshold", 2.0),
    ],
)
def test_recorded_known_settings_preserve_existing_reading(point, key, expected):
    raw = bytes.fromhex(REPLIES[point])
    readings = Decoder().feed(raw)
    assert {reading.key: reading.value for reading in readings} == {
        key: expected,
        f"raw_{point.lower()}": raw[8:-2].hex(),
    }


@pytest.mark.parametrize("point", ["0124", "0125", "0232", "0191"])
def test_original_unmapped_replies_keep_framing_at_every_split(point):
    raw = bytes.fromhex(REPLIES[point])
    expected = inventory([{"elapsed_ms": 0, "hex": raw.hex()}])
    for split in range(len(raw) + 1):
        assert (
            inventory(
                [
                    {"elapsed_ms": 0, "hex": raw[:split].hex()},
                    {"elapsed_ms": 0, "hex": raw[split:].hex()},
                ]
            )
            == expected
        )


@pytest.mark.parametrize("point", ["0124", "0125", "0232", "0191"])
def test_original_unmapped_reply_checksums_detect_every_single_bit_change(point):
    raw = bytes.fromhex(REPLIES[point])
    for bit in range(len(raw) * 8):
        damaged = bytearray(raw)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert checksum(damaged[:-2]) != int.from_bytes(damaged[-2:], "little")
