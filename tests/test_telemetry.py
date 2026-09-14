"""Observed telemetry channels, wire boundaries and per-channel invalid data."""

import struct

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

TEMP = bytes.fromhex("224000b70300002cc800e700ce00ac00c700d600b600d600c900c2000000654c")
FANS = bytes.fromhex("224000c900000010565c664404fa5e44bff1")
EXPECTED = {
    "temperature_supply": 20.0,
    "temperature_extract": 23.1,
    "temperature_exhaust": 20.6,
    "temperature_fresh": 17.2,
    "temperature_before_evaporator": 19.9,
    "temperature_evaporator": 21.4,
    "temperature_after_preheater": 18.2,
    "temperature_before_condenser": 21.4,
    "temperature_condenser": 20.1,
    "temperature_compressor": 19.4,
    "fan_supply_rpm": pytest.approx(921.44275),
    "fan_extract_rpm": pytest.approx(891.90649),
}


def test_every_split_and_single_byte_delivery():
    stream = TEMP + FANS
    for split in range(len(stream) + 1):
        decoder = Decoder()
        result = decoder.feed(stream[:split]) + decoder.feed(stream[split:])
        assert {r.key: r.value for r in result} == EXPECTED
        assert decoder.stats.accepted == 2
    decoder = Decoder()
    assert {
        r.key: r.value for byte in stream for r in decoder.feed(bytes([byte]))
    } == EXPECTED


def test_corrupt_long_frame_then_recover():
    for frame in (TEMP, FANS):
        for bit in range(len(frame) * 8):
            damaged = bytearray(frame)
            damaged[bit // 8] ^= 1 << (bit % 8)
            decoder = Decoder()
            assert decoder.feed(damaged + frame) == Decoder().feed(frame)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 10001])
def test_bad_fan_channel_does_not_hide_valid_sibling(value):
    readings = Decoder._readings("fan_speeds", struct.pack("<2f", value, 900))
    assert {r.key: r.value for r in readings} == {"fan_extract_rpm": 900}


@pytest.mark.parametrize("value", [0xFFFF, 0xFF9C, 0x7FFF, 1501])
def test_undocumented_negative_or_error_value_is_not_published(value):
    message = bytearray(TEMP[:-2])
    message[14:16] = value.to_bytes(2, "little")  # T3 only
    frame = message + checksum(message).to_bytes(2, "little")
    decoded = {r.key: r.value for r in Decoder().feed(frame)}
    assert "temperature_fresh" not in decoded
    assert len(decoded) == 9
    assert decoded["temperature_extract"] == 23.1


def test_unknown_eleventh_slot_ignored_and_wrong_length_rejected():
    message = bytearray(TEMP[:-2])
    message[-2:] = b"\xff\xff"
    frame = message + checksum(message).to_bytes(2, "little")
    assert Decoder().feed(frame) == Decoder().feed(TEMP)
    assert Decoder._readings("temperatures", TEMP[8:-3]) == []
    assert Decoder._readings("fan_speeds", FANS[8:-3]) == []
