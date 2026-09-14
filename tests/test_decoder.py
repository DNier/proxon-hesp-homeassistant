"""Recorded vectors, stream boundaries and invalid input regression tests."""

import random
import struct

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder


def test_documented_checksum_vector():
    assert checksum(bytes.fromhex("10800060010000040100")) == 0xE149
    assert checksum(bytes(7)) is None
    assert checksum(bytes(121)) is None


def test_recorded_values(frames):
    decoder = Decoder()
    values = {r.key: r.value for r in decoder.feed(b"".join(frames.values()))}
    assert values == {
        "room_temperature": pytest.approx(22.622492, abs=0.0001),
        "target_temperature": 21.0,
        "operating_mode": "eco_summer",
        "fan_level": 3,
    }
    assert decoder.stats.accepted == 4


def test_every_split_and_single_bytes(frames):
    stream = b"".join(frames.values())
    expected = Decoder().feed(stream)
    for split in range(len(stream) + 1):
        decoder = Decoder()
        assert decoder.feed(stream[:split]) + decoder.feed(stream[split:]) == expected
    decoder = Decoder()
    assert [r for b in stream for r in decoder.feed(bytes([b]))] == expected


def test_noise_corruption_and_partial_start(frames):
    valid = frames["0xe1"]
    corrupt = bytearray(valid)
    corrupt[-1] ^= 1
    decoder = Decoder()
    stream = valid[4:] + bytes(corrupt) + b"noise" + valid
    assert [r.value for r in decoder.feed(stream)] == [3]
    assert decoder.stats.checksum_rejected == 1
    assert len(decoder.buffer) < 14


def test_wrong_node_type_length_and_reserved_are_ignored(frames):
    valid = frames["0xe1"]
    for index, value in [(0, 0x10), (2, 7), (5, 1), (7, 0xE0)]:
        bad = bytearray(valid)
        bad[index] = value
        decoder = Decoder()
        assert decoder.feed(bytes(bad)) == []
        assert decoder.feed(valid)[0].value == 3


def test_noise_cannot_grow_retained_buffer():
    decoder = Decoder()
    randomizer = random.Random(42)
    for _ in range(100):
        decoder.feed(randomizer.randbytes(4096))
        assert len(decoder.buffer) < 14


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -100.0, 1000.0])
def test_temperature_rejects_nonphysical_values(value):
    assert Decoder._value("room_temperature", struct.pack("<f", value)) is None


def test_unknown_enum_and_level_do_not_become_zero():
    assert Decoder._value("operating_mode", b"\xff\xff") is None
    assert Decoder._value("fan_level", b"\x05\x00") is None
