"""Independent wire checksums, derivation, and corruption regressions."""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import BYTE_TRANSFORM, checksum
from tools.derive_checksum import derive

FRAMES = [
    bytes.fromhex(value)
    for value in json.loads(
        (Path(__file__).parent / "fixtures/checksum_frames.json").read_text()
    )
]


def test_public_reference_uniquely_derives_algorithm():
    assert derive() == (BYTE_TRANSFORM, 0xFFFF)


@pytest.mark.parametrize("frame", FRAMES)
def test_recorded_checksums_and_every_single_bit_corruption(frame):
    # Expected checksums come from the wire, never from this implementation.
    expected = int.from_bytes(frame[-2:], "little")
    assert checksum(frame[:-2]) == expected
    for bit in range(len(frame) * 8):
        damaged = bytearray(frame)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert checksum(damaged[:-2]) != int.from_bytes(damaged[-2:], "little")


def test_explicit_word_crc_matches_existing_transform_and_recorded_wire():
    """Independent polynomial description from the external protocol proposal."""

    def step(state):
        for _ in range(16):
            state = (state >> 1) ^ 0x8048 if state & 1 else state >> 1
        return state

    # Both mappings are linear, so equality on the basis proves the whole step.
    assert tuple(step(1 << bit) for bit in range(16)) == BYTE_TRANSFORM
    for frame in FRAMES:
        state = 0xFFFF
        for byte in frame[:-2]:
            state = step(state ^ byte)
        assert state == int.from_bytes(frame[-2:], "little")
