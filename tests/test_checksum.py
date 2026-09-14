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
