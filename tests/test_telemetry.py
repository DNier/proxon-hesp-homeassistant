"""Observed telemetry channels, wire boundaries and per-channel invalid data."""

import struct

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import TEMPERATURE_KEYS, Decoder

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

# Fixed frames recorded after the 2026-10-09 negative T6 display reference.
# Only anonymous temperature payloads and their original checksums are retained.
NEGATIVE_TEMPERATURES = (
    (
        "224000b70300002cd701e700f7ff26006200f3ff32001301c70158030000afeb",
        (47.1, 23.1, -0.9, 3.8, 9.8, -1.3, 5.0, 27.5, 45.5, 85.6),
    ),
    (
        "224000b70300002cdb01e700f6ff26006100f2ff32001401cf015b03000021e1",
        (47.5, 23.1, -1.0, 3.8, 9.7, -1.4, 5.0, 27.6, 46.3, 85.9),
    ),
)


def temperature_frame(channel, value):
    body = bytearray(TEMP[:-2])
    offset = 8 + 2 * channel
    body[offset : offset + 2] = value.to_bytes(2, "little")
    return body + checksum(body).to_bytes(2, "little")


@pytest.mark.parametrize("raw,values", NEGATIVE_TEMPERATURES)
def test_recorded_negative_temperatures_at_every_split(raw, values):
    frame = bytes.fromhex(raw)
    expected = dict(zip(TEMPERATURE_KEYS, values, strict=True))
    for split in range(len(frame) + 1):
        decoder = Decoder()
        readings = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in readings} == expected
        assert decoder.stats.accepted == 1
    decoder = Decoder()
    assert {
        r.key: r.value for byte in frame for r in decoder.feed(bytes([byte]))
    } == expected


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
    for frame in (TEMP, FANS, bytes.fromhex(NEGATIVE_TEMPERATURES[0][0])):
        for bit in range(len(frame) * 8):
            damaged = bytearray(frame)
            damaged[bit // 8] ^= 1 << (bit % 8)
            decoder = Decoder()
            assert decoder.feed(damaged + frame) == Decoder().feed(frame)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 10001])
def test_bad_fan_channel_does_not_hide_valid_sibling(value):
    readings = Decoder._readings("fan_speeds", struct.pack("<2f", value, 900))
    assert {r.key: r.value for r in readings} == {"fan_extract_rpm": 900}


@pytest.mark.parametrize("channel", [2, 5])
@pytest.mark.parametrize("value", [0xFFFF, 0x7FFF, 0x8000, 0xFE0B, 1501])
def test_sentinel_or_out_of_range_temperature_preserves_valid_siblings(channel, value):
    decoded = {
        r.key: r.value for r in Decoder().feed(temperature_frame(channel, value))
    }
    expected = {k: EXPECTED[k] for k in TEMPERATURE_KEYS}
    del expected[TEMPERATURE_KEYS[channel]]
    assert decoded == expected


@pytest.mark.parametrize("channel", [2, 5])
@pytest.mark.parametrize(
    "raw,expected",
    [
        (0xFE0C, -50.0),
        (0xFE0D, -49.9),
        (0xFF9C, -10.0),
        (0xFFFE, -0.2),
        (0, 0.0),
        (1, 0.1),
        (1500, 150.0),
    ],
)
def test_signed_temperature_receive_boundaries(channel, raw, expected):
    values = {r.key: r.value for r in Decoder().feed(temperature_frame(channel, raw))}
    assert len(values) == 10
    assert values[TEMPERATURE_KEYS[channel]] == expected


@pytest.mark.parametrize("channel", [2, 5])
def test_temperature_zero_crossing_keeps_ffff_uninterpreted(channel):
    decoder = Decoder()
    for raw, expected in [(0xFFFE, -0.2), (0xFFFF, None), (0, 0.0), (1, 0.1)]:
        values = {r.key: r.value for r in decoder.feed(temperature_frame(channel, raw))}
        assert values.get(TEMPERATURE_KEYS[channel]) == expected
        assert values["temperature_extract"] == 23.1


@pytest.mark.parametrize("index,value", [(0, 0x11), (1, 0x41), (2, 7), (5, 1), (7, 0)])
def test_negative_temperature_frame_keeps_identity_and_length_guards(index, value):
    body = bytearray(bytes.fromhex(NEGATIVE_TEMPERATURES[0][0])[:-2])
    body[index] = value
    frame = body + checksum(body).to_bytes(2, "little")
    assert Decoder().feed(frame) == []


def test_unknown_eleventh_slot_ignored_and_wrong_length_rejected():
    message = bytearray(TEMP[:-2])
    message[-2:] = b"\xff\xff"
    frame = message + checksum(message).to_bytes(2, "little")
    assert Decoder().feed(frame) == Decoder().feed(TEMP)
    assert Decoder._readings("temperatures", TEMP[8:-3]) == []
    assert Decoder._readings("fan_speeds", FANS[8:-3]) == []
