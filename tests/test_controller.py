"""Independent recorded controller responses and reference coverage boundaries."""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.decoder import Decoder

FRAMES = {
    key: bytes.fromhex(value)
    for key, value in json.loads(
        (Path(__file__).parent / "fixtures/controller_frames.json").read_text()
    ).items()
}


def test_recorded_controller_values_and_every_split():
    stream = b"".join(FRAMES.values())
    expected = {
        "controller_fan_level": 3,
        "fan_supply_control": 5200.0,
        "fan_extract_control": 5200.0,
        "bypass_status": True,
        "compressor_rpm": 0.0,
        "fan_supply_rpm": pytest.approx(1788.05444),
        "fan_extract_rpm": pytest.approx(1754.57190),
        "temperature_supply": 22.8,
        "temperature_extract": 23.8,
        "temperature_exhaust": 22.9,
        "temperature_fresh": 21.4,
        "temperature_before_evaporator": 22.7,
        "temperature_evaporator": 23.4,
        "temperature_after_preheater": 22.2,
        "temperature_before_condenser": 23.5,
        "temperature_condenser": 22.9,
        "temperature_compressor": 22.5,
        "filter_days": 114,
        "device_clock": "00:02:16",
        "uptime": 35831810,
        "counter_02d0": 42236,
        "counter_02d1": 9607,
        "counter_02d2": 38481,
        "counter_02d3": 2414,
        "counter_02d4": 26708,
        "counter_02d5": 5,
        "counter_02d7": 95282,
        "counter_02d9": 1818,
    }
    for split in range(len(stream) + 1):
        decoder = Decoder()
        readings = decoder.feed(stream[:split]) + decoder.feed(stream[split:])
        assert {
            r.key: r.value for r in readings if not r.key.startswith("raw_")
        } == expected
        assert next(r.value for r in readings if r.key == "raw_0116") == "64005a00"


@pytest.mark.parametrize("index,value", [(0, 0x11), (1, 0x41), (2, 7), (5, 1), (7, 4)])
def test_response_identity_cannot_be_confused_with_panel_or_other_node(index, value):
    bad = bytearray(FRAMES["0x00ed"])
    bad[index] = value
    assert Decoder().feed(bytes(bad)) == []


def test_corrupt_response_is_rejected_and_recovers():
    valid = FRAMES["0x00ed"]
    bad = bytearray(valid)
    bad[-1] ^= 1
    decoder = Decoder()
    assert [r.value for r in decoder.feed(bytes(bad) + valid)] == [114]
    assert decoder.stats.checksum_rejected == 1


@pytest.mark.parametrize("dp", ["0x02df", "0x02d6"])
def test_unverified_arrays_do_not_publish(dp):
    assert Decoder().feed(FRAMES[dp]) == []


def test_unavailable_unsigned_sentinel():
    assert Decoder._value("filter_days", b"\xff" * 4) is None
    assert Decoder._value("uptime", bytes(4)) == 0


def test_recorded_clock_and_corruption():
    frame = bytes.fromhex("2240003003000008d6fc0000d2f8")
    for split in range(len(frame) + 1):
        decoder = Decoder()
        values = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in values}["device_clock"] == "22:38:31"
    damaged = frame[:-1] + bytes([frame[-1] ^ 1])
    assert Decoder().feed(damaged) == []


@pytest.mark.parametrize("value", [24, 60 << 5, 60 << 11, 1 << 17])
def test_invalid_clock_fields(value):
    from custom_components.proxon_hesp.hesp.decoder import decode_clock

    assert decode_clock(value.to_bytes(4, "little")) is None
