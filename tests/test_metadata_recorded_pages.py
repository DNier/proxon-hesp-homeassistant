"""Original P 2H-L metadata exchanges, with no inferred catalog or code meanings."""

import copy
import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from tools.address_analysis import analyze_exchanges
from tools.audit_metadata import PAGE_FORMAT, audit_metadata
from tools.inventory_capture import inventory

SOURCE = json.loads(
    (Path(__file__).parent / "fixtures/metadata_pages_recorded.json").read_text()
)
POINTS = (0x0033, 0x0034, 0x0038, 0x0039)


def exchange(point, offset):
    """Select an unchanged original query/reply pair from the recorded fixture."""
    register = (point | (offset << 16)).to_bytes(4, "little").hex()
    for index, row in enumerate(SOURCE["frames"]):
        if row["hex"].startswith("108000" + register):
            return copy.deepcopy(SOURCE["frames"][index : index + 2])
    raise AssertionError("Requested recorded exchange is missing")


def test_recorded_queries_and_replies_preserve_original_checksums_and_inventory():
    assert SOURCE["format"] == PAGE_FORMAT
    assert len(SOURCE["frames"]) == 72
    for row in SOURCE["frames"]:
        raw = bytes.fromhex(row["hex"])
        assert checksum(raw[:-2]) == int.from_bytes(raw[-2:], "little")
        if raw[:3] == bytes.fromhex("108000"):
            assert len(raw) == 12
            assert raw[8:-2] == bytes.fromhex("4000")
        elif raw[:3] == bytes.fromhex("224000"):
            assert len(raw) == 138
        else:
            assert raw[:3] == bytes.fromhex("244000")
            assert len(raw) == 12
            assert raw[8:-2] == bytes.fromhex("0100")
    report = inventory(SOURCE["frames"], include_frame_observations=True)
    assert report["frames"] == 72
    assert report["unparsed_bytes"] == 0
    exchanges = analyze_exchanges(report)
    assert len(exchanges["pairs"]) == 36
    assert exchanges["unmatched"] == []
    assert (
        sum(
            pair["kind"] == "query_metadata_negative_response"
            for pair in exchanges["pairs"]
        )
        == 16
    )


def test_original_pages_cover_163_aligned_rows_and_consistent_overlap():
    before = copy.deepcopy(SOURCE)
    result = audit_metadata(SOURCE)
    assert SOURCE == before
    assert len(result["pages"]) == 20
    assert len(result["rows"]) == result["observed_extent"] == 163
    assert [row["index"] for row in result["rows"]] == list(range(163))
    assert result["missing_ranges"] == {f"0x{point:04X}": [] for point in POINTS}
    assert result["required_columns_aligned_over_observed_extent"] is True
    assert result["units_present"] is True
    for point in POINTS:
        pages = [page for page in result["pages"] if page["dp"] == f"0x{point:04X}"]
        assert [page["offset"] for page in pages] == [0, 64, 96, 98, 99]
        assert all(page["entries"] == 64 for page in pages)
    assert result["rows"][21] == {
        "index": 21,
        "dp": "0x0232",
        "type_code": "0x0204",
        "mask_code": "0x0055",
        "unit_code": "0x0000",
    }
    assert result["rows"][76] == {
        "index": 76,
        "dp": "0x0124",
        "type_code": "0x0203",
        "mask_code": "0x00C0",
        "unit_code": "0x0008",
    }
    assert result["rows"][162] == {
        "index": 162,
        "dp": "0x01F5",
        "type_code": "0x0001",
        "mask_code": "0x0055",
        "unit_code": "0x0005",
    }
    assert result["catalog_length"] is None
    assert result["semantics"] == "unconfirmed_type_mask_and_unit_codes"


def test_negative_offset_replies_are_visible_without_becoming_catalog_rows():
    result = audit_metadata(SOURCE)
    assert len(result["negative_responses"]) == 16
    assert result["unanswered_queries"] == []
    assert result["duplicate_reply_frames"] == []
    for point in POINTS:
        replies = [
            row for row in result["negative_responses"] if row["dp"] == f"0x{point:04X}"
        ]
        assert [row["offset"] for row in replies] == [128, 112, 104, 100]
        assert all(row["payload_hex"] == "0100" for row in replies)
        assert all(
            row["register_id"] == f"0x{(row['offset'] << 16) | point:08X}"
            for row in replies
        )
        assert all(0 < row["delta_ms"] < 100 for row in replies)
    assert result["observed_extent"] == 163
    assert result["catalog_length"] is None


@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("offset", [99, 100])
@pytest.mark.parametrize("frame_index", [0, 1])
def test_original_exchange_handles_every_frame_fragment_boundary(
    point, offset, frame_index
):
    records = exchange(point, offset)
    expected = audit_metadata({"format": PAGE_FORMAT, "frames": records})
    original = records[frame_index]
    raw = bytes.fromhex(original["hex"])
    for split in range(len(raw) + 1):
        assert (
            audit_metadata(
                {
                    "format": PAGE_FORMAT,
                    "chunks": records[:frame_index]
                    + [
                        {
                            "elapsed_ms": original["elapsed_ms"],
                            "hex": raw[:split].hex(),
                        },
                        {
                            "elapsed_ms": original["elapsed_ms"],
                            "hex": raw[split:].hex(),
                        },
                    ]
                    + records[frame_index + 1 :],
                }
            )
            == expected
        )


@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("offset", [99, 100])
def test_recorded_page_and_negative_reply_reject_every_single_bit_change(point, offset):
    raw = bytes.fromhex(exchange(point, offset)[1]["hex"])
    for bit in range(len(raw) * 8):
        damaged = bytearray(raw)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert checksum(damaged[:-2]) != int.from_bytes(damaged[-2:], "little")
    for length in range(len(raw)):
        assert inventory([{"elapsed_ms": 0, "hex": raw[:length].hex()}])["frames"] == 0


@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("offset", [99, 100])
@pytest.mark.parametrize("mutation", ["checksum", "truncated"])
def test_damaged_original_exchange_cannot_enter_metadata_audit(point, offset, mutation):
    records = exchange(point, offset)
    damaged = bytearray.fromhex(records[1]["hex"])
    if mutation == "checksum":
        damaged[-1] ^= 1
    else:
        damaged.pop()
    records[1]["hex"] = damaged.hex()
    with pytest.raises(ValueError):
        audit_metadata({"format": PAGE_FORMAT, "frames": records})


def test_original_metadata_is_offline_only_and_has_no_live_reading_mapping():
    decoder = Decoder()
    assert (
        decoder.feed(b"".join(bytes.fromhex(row["hex"]) for row in SOURCE["frames"]))
        == []
    )
    assert decoder.stats.accepted == 0
