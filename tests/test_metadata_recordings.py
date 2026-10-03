"""Independent public wire captures of the extended metadata response shape."""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from tools.audit_metadata import audit_metadata
from tools.inventory_capture import inventory

REPLIES = json.loads(
    (Path(__file__).parent / "fixtures/metadata_replies.json").read_text()
)
ACK = bytes.fromhex("234000270200000039a1")
QUERY = bytes.fromhex("108000d4020000040100a163")


def chunks(*parts):
    return [{"elapsed_ms": 42, "hex": part.hex()} for part in parts]


@pytest.mark.parametrize("raw", REPLIES.values())
def test_recorded_checksum_and_every_single_bit_corruption(raw):
    frame = bytes.fromhex(raw)
    assert len(frame) == 138
    assert checksum(frame[:-2]) == int.from_bytes(frame[-2:], "little")
    for bit in range(len(frame) * 8):
        damaged = bytearray(frame)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert checksum(damaged[:-2]) != int.from_bytes(damaged[-2:], "little")


@pytest.mark.parametrize("raw", REPLIES.values())
def test_fragmented_metadata_followed_by_query_and_empty_ack(raw):
    stream = bytes.fromhex(raw) + QUERY + ACK
    expected = inventory(chunks(stream))
    assert expected["frames"] == 3
    assert expected["unparsed_bytes"] == 0
    assert expected["groups"]["234000/0x0227/0"]["payload_bytes"] == 0
    for split in range(len(stream) + 1):
        assert inventory(chunks(stream[:split], stream[split:])) == expected


def test_recorded_columns_align_without_interpreting_codes():
    result = audit_metadata(REPLIES)
    assert len(result["rows"]) == 64
    assert result["rows"][24] == {
        "dp": "0x0227",
        "type_code": "0x0204",
        "mask_code": "0x00FF",
    }
    assert result["rows"][-1] == {
        "dp": "0x010D",
        "type_code": "0x0203",
        "mask_code": "0x0055",
    }
    assert result["semantics"] == "unconfirmed_type_and_mask_codes"


@pytest.mark.parametrize(
    "mutation", ["truncated", "corrupt", "identity", "dp", "reserved", "extra"]
)
def test_bad_or_unproven_extended_frames_cannot_be_aligned(mutation):
    data = dict(REPLIES)
    frame = bytearray.fromhex(data["0033"])
    if mutation == "truncated":
        frame = frame[:128]
    elif mutation == "corrupt":
        frame[-1] ^= 1
    elif mutation == "extra":
        frame += QUERY
    else:
        offset = {"identity": 0, "dp": 3, "reserved": 5}[mutation]
        frame[offset] ^= 1
        frame[-2:] = checksum(frame[:-2]).to_bytes(2, "little")
    data["0033"] = frame.hex()
    with pytest.raises(ValueError):
        audit_metadata(data)


def test_extended_metadata_does_not_create_live_entities_or_readings():
    decoder = Decoder()
    assert decoder.feed(b"".join(bytes.fromhex(v) for v in REPLIES.values())) == []
    assert decoder.stats.accepted == 0


def test_checksum_remains_bounded():
    assert checksum(bytes(137)) is None
