"""Synthetic offset/unit-page preparation, never additional recorded semantics."""

import copy
import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from tools.address_analysis import analyze_exchanges
from tools.audit_metadata import PAGE_FORMAT, audit_metadata, main
from tools.inventory_capture import inventory

POINTS = (0x0033, 0x0034, 0x0038, 0x0039)


def frame(point, offset=0, *, query=False, count=1, values=None, header=None):
    if query:
        payload = count.to_bytes(2, "little")
    else:
        values = values if values is not None else [i + offset for i in range(64)]
        payload = b"".join(value.to_bytes(2, "little") for value in values)
    body = bytes.fromhex(header or ("108000" if query else "224000"))
    body += (point | (offset << 16)).to_bytes(4, "little")
    body += bytes([(len(payload) * 2) % 256]) + payload
    return body + checksum(body).to_bytes(2, "little")


def records(*wire):
    return [{"elapsed_ms": i * 10, "hex": raw.hex()} for i, raw in enumerate(wire)]


def negative(point=0x0033, offset=100):
    """Synthetic counterexamples use only the recorded negative payload shape."""
    return frame(point, offset, values=[1], header="244000")


def source(offsets=(0, 64, 86), points=POINTS, *, count=1):
    wire = []
    for offset in offsets:
        for point in points:
            wire.extend(
                (frame(point, offset, query=True, count=count), frame(point, offset))
            )
    return {"format": PAGE_FORMAT, "frames": records(*wire)}


def test_published_reconstructed_count_64_query_matches_existing_crc_and_inventory():
    # Markus's published reconstruction is a compatibility vector, not an
    # original timed wire recording or evidence for a corresponding response.
    raw = bytes.fromhex("10800033000000044000aece")
    assert checksum(raw[:-2]) == int.from_bytes(raw[-2:], "little") == 0xCEAE
    report = inventory(records(raw), include_frame_observations=True)
    assert report["frames"] == 1
    assert report["unparsed_bytes"] == 0
    assert report["groups"]["108000/0x0033/2"]["values"] == ["4000"]
    assert analyze_exchanges(report)["counts"]["pairs"] == 0


def test_count_64_pages_merge_overlapping_offset_99_without_proving_catalog_length():
    # Synthetic coverage of the reported request/offset form; this is not
    # Markus's missing original 163-entry QUERY/RESPONSE recording.
    data = source(offsets=(0, 64, 99), count=64)
    before = copy.deepcopy(data)
    result = audit_metadata(data)
    assert data == before
    assert len(result["pages"]) == 12
    assert [page["offset"] for page in result["pages"]] == [0] * 4 + [64] * 4 + [99] * 4
    assert all(page["entries"] == 64 for page in result["pages"])
    assert result["rows"][-1] == {
        "index": 162,
        "dp": "0x00A2",
        "type_code": "0x00A2",
        "mask_code": "0x00A2",
        "unit_code": "0x00A2",
    }
    assert result["missing_ranges"] == {f"0x{point:04X}": [] for point in POINTS}
    assert result["required_columns_aligned_over_observed_extent"] is True
    assert result["catalog_length"] is None
    assert result["selector_interpretation"] == "candidate_element_offset"
    assert "°C" not in json.dumps(result)


def test_legacy_and_count_64_queries_can_share_a_group_after_separate_replies():
    data = {
        "format": PAGE_FORMAT,
        "frames": records(
            frame(0x0033, query=True),
            frame(0x0033),
            frame(0x0033, query=True, count=64),
            frame(0x0033),
        ),
    }
    result = audit_metadata(data)
    assert len(result["pages"]) == 2
    assert len(result["rows"]) == 64
    assert result["catalog_length"] is None
    assert result["query_count"] == (
        "0100: uint16 count 1; 4000: uint16 count 64; other counts unsupported"
    )


def test_count_64_query_and_long_reply_keep_checksum_framing_at_every_split():
    wire = frame(0x0039, 99, query=True, count=64) + frame(0x0039, 99)
    expected = audit_metadata(
        {"format": PAGE_FORMAT, "chunks": [{"elapsed_ms": 42, "hex": wire.hex()}]}
    )
    assert expected["pages"][0]["register_id"] == "0x00630039"
    assert expected["pages"][0]["entries"] == 64
    for split in range(len(wire) + 1):
        assert (
            audit_metadata(
                {
                    "format": PAGE_FORMAT,
                    "chunks": [
                        {"elapsed_ms": 42, "hex": wire[:split].hex()},
                        {"elapsed_ms": 42, "hex": wire[split:].hex()},
                    ],
                }
            )
            == expected
        )


@pytest.mark.parametrize("offset", [0, 64])
@pytest.mark.parametrize("count", [0, 2, 63, 65, 0x4000, 0xFFFF])
def test_other_query_counts_are_rejected_with_or_without_selector(offset, count):
    data = {
        "format": PAGE_FORMAT,
        "frames": records(frame(0x0033, offset, query=True, count=count)),
    }
    before = copy.deepcopy(data)
    with pytest.raises(ValueError):
        audit_metadata(data)
    assert data == before


@pytest.mark.parametrize("offset", [0, 64])
@pytest.mark.parametrize(
    "payload", [b"", b"\x40", b"\x40\x00\x00", b"\x40\x00\x00\x00"]
)
def test_count_64_looking_payloads_require_exact_uint16_width(offset, payload):
    header = frame(0x0033, offset, query=True, count=64)[:7]
    body = header + bytes([len(payload) * 2]) + payload
    raw = body + checksum(body).to_bytes(2, "little")
    with pytest.raises(ValueError):
        audit_metadata({"format": PAGE_FORMAT, "frames": records(raw)})


@pytest.mark.parametrize("counts", [(1, 64), (64, 1), (64, 64)])
def test_different_query_counts_do_not_disambiguate_overlapping_same_page(counts):
    wire = (
        frame(0x0033, 64, query=True, count=counts[0]),
        frame(0x0033, 64, query=True, count=counts[1]),
        frame(0x0033, 64),
    )
    with pytest.raises(ValueError, match="overlapping_request"):
        audit_metadata({"format": PAGE_FORMAT, "frames": records(*wire)})


def test_unanswered_count_64_query_is_visible_without_extending_observed_catalog():
    data = source(offsets=(0,), count=64)
    data["frames"].append(
        {"elapsed_ms": 100, "hex": frame(0x0033, 99, query=True, count=64).hex()}
    )
    result = audit_metadata(data)
    assert result["unanswered_queries"] == [
        {
            "register_id": "0x00630033",
            "query_frame_index": 8,
            "reason": "end_of_capture",
        }
    ]
    assert result["observed_extent"] == 64
    assert result["catalog_length"] is None


@pytest.mark.parametrize("point", POINTS)
def test_negative_metadata_response_is_separate_from_pages_and_unanswered(point):
    data = source(offsets=(0,), count=64)
    data["frames"].extend(
        [
            {"elapsed_ms": 100, "hex": frame(point, 100, query=True, count=64).hex()},
            {"elapsed_ms": 128, "hex": negative(point).hex()},
        ]
    )
    before = copy.deepcopy(data)
    result = audit_metadata(data)
    assert data == before
    assert result["negative_responses"] == [
        {
            "dp": f"0x{point:04X}",
            "register_id": f"0x0064{point:04X}",
            "offset": 100,
            "query_frame_index": 8,
            "response_frame_index": 9,
            "delta_ms": 28,
            "payload_hex": "0100",
        }
    ]
    assert result["unanswered_queries"] == []
    assert len(result["pages"]) == 4
    assert result["observed_extent"] == 64
    assert len(result["rows"]) == 64
    assert result["catalog_length"] is None


@pytest.mark.parametrize("offset", [0, 100])
@pytest.mark.parametrize("count", [1, 64])
def test_negative_only_report_preserves_identity_without_inventing_catalog(
    offset, count
):
    result = audit_metadata(
        {
            "format": PAGE_FORMAT,
            "frames": records(
                frame(0x0039, offset, query=True, count=count),
                negative(0x0039, offset),
            ),
        }
    )
    assert result["negative_responses"][0]["register_id"] == f"0x{offset:04X}0039"
    assert result["negative_responses"][0]["offset"] == offset
    assert result["pages"] == result["rows"] == result["unanswered_queries"] == []
    assert result["observed_extent"] == 0
    assert result["required_columns_aligned_over_observed_extent"] is False
    assert result["units_present"] is False
    assert result["catalog_length"] is None


def test_negative_reply_and_query_keep_fragmentation_and_crc_at_every_split():
    wire = frame(0x0039, 100, query=True, count=64) + negative(0x0039)
    expected = audit_metadata(
        {"format": PAGE_FORMAT, "chunks": [{"elapsed_ms": 42, "hex": wire.hex()}]}
    )
    for split in range(len(wire) + 1):
        assert (
            audit_metadata(
                {
                    "format": PAGE_FORMAT,
                    "chunks": [
                        {"elapsed_ms": 42, "hex": wire[:split].hex()},
                        {"elapsed_ms": 42, "hex": wire[split:].hex()},
                    ],
                }
            )
            == expected
        )
    for bit in range(len(wire) * 8):
        corrupted = bytearray(wire)
        corrupted[bit // 8] ^= 1 << (bit % 8)
        with pytest.raises(ValueError):
            audit_metadata({"format": PAGE_FORMAT, "frames": records(corrupted)})
    for length in range(len(negative())):
        assert inventory(records(negative()[:length]))["frames"] == 0
    assert Decoder().feed(wire) == []


@pytest.mark.parametrize(
    "raw",
    [
        frame(0x0040, 100, values=[1], header="244000"),
        frame(0x0033, 100, values=[1], header="344000"),
        frame(0x0033, 100, values=[1], header="244007"),
        frame(0x0033, 100, values=[0], header="244000"),
        frame(0x0033, 100, values=[2], header="244000"),
        frame(0x0033, 100, values=[], header="244000"),
        frame(0x0033, 100, values=[1, 0], header="244000"),
    ],
)
def test_negative_selector_extension_rejects_other_routes_codes_and_payload_shapes(raw):
    assert inventory(records(raw))["unparsed_bytes"] == len(raw)
    with pytest.raises(ValueError):
        audit_metadata({"format": PAGE_FORMAT, "frames": records(raw)})


@pytest.mark.parametrize("offset", [0, 100])
@pytest.mark.parametrize(
    "wire,reason",
    [
        (lambda offset: [negative(offset=offset)], "orphan_reply"),
        (
            lambda offset: [
                frame(0x0033, offset, query=True),
                negative(offset=offset + 1),
            ],
            "wrong_data_point",
        ),
        (
            lambda offset: [
                frame(0x0033, offset, query=True),
                frame(0x0033, offset, query=True),
                negative(offset=offset),
            ],
            "overlapping_request",
        ),
    ],
)
def test_negative_orphan_wrong_offset_and_ambiguous_exchange_are_rejected(
    offset, wire, reason
):
    with pytest.raises(ValueError, match=reason):
        audit_metadata({"format": PAGE_FORMAT, "frames": records(*wire(offset))})


def test_late_negative_metadata_response_is_rejected_instead_of_a_catalog_end():
    with pytest.raises(ValueError, match="late_reply"):
        audit_metadata(
            {
                "format": PAGE_FORMAT,
                "frames": [
                    {"elapsed_ms": 0, "hex": frame(0x0033, 100, query=True).hex()},
                    {"elapsed_ms": 1001, "hex": negative().hex()},
                ],
            }
        )


def test_identical_negative_duplicate_is_visible_without_another_page_or_negative():
    result = audit_metadata(
        {
            "format": PAGE_FORMAT,
            "frames": records(frame(0x0033, 100, query=True), negative(), negative()),
        }
    )
    assert len(result["negative_responses"]) == 1
    assert result["duplicate_reply_frames"] == [2]
    assert result["pages"] == []


@pytest.mark.parametrize("first_negative", [False, True])
def test_conflicting_positive_and_negative_reply_is_rejected(first_negative):
    replies = [frame(0x0033, 100), negative()]
    if first_negative:
        replies.reverse()
    with pytest.raises(ValueError, match="duplicate_reply"):
        audit_metadata(
            {
                "format": PAGE_FORMAT,
                "frames": records(frame(0x0033, 100, query=True), *replies),
            }
        )


@pytest.mark.parametrize("first_negative", [False, True])
@pytest.mark.parametrize("prior_queries", [1, 2])
def test_old_opposite_reply_after_repeated_same_page_queries_is_not_a_duplicate(
    first_negative, prior_queries
):
    """An earlier pair must not hide a contradiction to the latest paired query."""
    first = negative() if first_negative else frame(0x0033, 100)
    latest = frame(0x0033, 100) if first_negative else negative()
    wire = []
    for _ in range(prior_queries):
        wire.extend([frame(0x0033, 100, query=True, count=64), first])
    wire.extend([frame(0x0033, 100, query=True, count=64), latest, first])
    with pytest.raises(ValueError, match="duplicate_reply"):
        audit_metadata({"format": PAGE_FORMAT, "frames": records(*wire)})


@pytest.mark.parametrize("first_negative", [False, True])
@pytest.mark.parametrize("prior_queries", [1, 2])
def test_repeated_same_page_queries_allow_only_the_latest_identical_reply_duplicate(
    first_negative, prior_queries
):
    """Independent differing replies remain visible; the latest duplicate is safe."""
    first = negative() if first_negative else frame(0x0033, 100)
    latest = frame(0x0033, 100) if first_negative else negative()
    wire = []
    for _ in range(prior_queries):
        wire.extend([frame(0x0033, 100, query=True, count=64), first])
    wire.extend([frame(0x0033, 100, query=True, count=64), latest, latest])
    result = audit_metadata({"format": PAGE_FORMAT, "frames": records(*wire)})
    assert len(result["pages"]) == (1 if first_negative else prior_queries)
    assert len(result["negative_responses"]) == (prior_queries if first_negative else 1)
    assert result["unanswered_queries"] == []
    assert result["duplicate_reply_frames"] == [2 * (prior_queries + 1)]


def test_page_inventory_preserves_legacy_zero_keys_and_complete_offset_identity():
    wire = frame(0x0033) + frame(0x0033, 64) + frame(0x0039, 64)
    expected = inventory(
        [{"elapsed_ms": 42, "hex": wire.hex()}], include_frame_observations=True
    )
    assert set(expected["groups"]) == {
        "224000/0x0033/128",
        "224000/0x00400033/128",
        "224000/0x00400039/128",
    }
    assert "register_id" not in expected["groups"]["224000/0x0033/128"]
    assert expected["groups"]["224000/0x00400033/128"]["register_id"] == "0x00400033"
    assert expected["groups"]["224000/0x00400033/128"]["selector_offset"] == 64
    assert all(len(row) == 5 for row in expected["frame_observations"])
    for split in range(len(wire) + 1):
        assert (
            inventory(
                [
                    {"elapsed_ms": 42, "hex": wire[:split].hex()},
                    {"elapsed_ms": 42, "hex": wire[split:].hex()},
                ],
                include_frame_observations=True,
            )
            == expected
        )


@pytest.mark.parametrize("point", POINTS)
def test_new_page_forms_retain_crc_and_do_not_accept_any_single_bit_corruption(point):
    raw = frame(point, 64)
    for bit in range(len(raw) * 8):
        changed = bytearray(raw)
        changed[bit // 8] ^= 1 << (bit % 8)
        assert inventory(records(bytes(changed)))["unparsed_bytes"] > 0
    for length in range(len(raw)):
        assert inventory(records(raw[:length]))["frames"] == 0
    assert Decoder().feed(raw) == []


@pytest.mark.parametrize(
    "raw",
    [
        frame(0x0033, 64, header="324000"),
        frame(0x0033, 64, header="234000"),
        frame(0x0033, 64, values=[1, 2]),
        frame(0x0040, 64),
        frame(0x0040, 64, query=True, count=64),
        frame(0x0033, 64, query=True, count=65),
        frame(0x0033, 64, query=True, count=0),
        frame(0x0033, 64, query=True, header="108007"),
    ],
)
def test_selector_extension_stays_narrow(raw):
    assert inventory(records(raw))["unparsed_bytes"] == len(raw)


def test_units_zero_selector_response_is_not_an_empty_confirmation():
    units = frame(0x0039)
    ack = frame(0x0039, values=[], header="234000")
    empty_response = frame(0x0039, values=[])
    result = inventory(records(units, ack, empty_response))
    assert result["frames"] == 2
    assert result["unparsed_bytes"] == len(empty_response)
    assert result["groups"]["224000/0x0039/128"]["payload_bytes"] == 128
    assert result["groups"]["234000/0x0039/0"]["payload_bytes"] == 0


@pytest.mark.parametrize("counts", [(1, 1), (1, 64), (64, 1), (64, 64)])
def test_address_matcher_uses_the_whole_register_id_when_pages_interleave(counts):
    report = inventory(
        records(
            frame(0x0033, query=True, count=counts[0]),
            frame(0x0033, 64, query=True, count=counts[1]),
            frame(0x0033, 64),
            frame(0x0033),
        ),
        include_frame_observations=True,
    )
    result = analyze_exchanges(report)
    assert result["counts"]["pairs"] == 2
    assert not result["unmatched"]
    assert "register_id" not in result["pairs"][0]["request"]
    assert result["pairs"][1]["request"]["register_id"] == "0x00400033"
    assert result["pairs"][1]["reply"]["register_id"] == "0x00400033"
    assert result["pairs"][1]["reply"]["dp"] == "0x0033"


@pytest.mark.parametrize(
    "extra",
    [
        {"register_id": 0x00400033, "selector_offset": 64},
        {"register_id": 0x00400033},
        {"selector_offset": 64},
    ],
)
def test_caller_derived_fields_cannot_match_a_different_page_or_cause_keyerror(extra):
    report = inventory(
        records(frame(0x0033, query=True), frame(0x0033, 64)),
        include_frame_observations=True,
    )
    report["frame_observations"][0].update(extra)
    result = analyze_exchanges(report)
    assert result["counts"]["pairs"] == 0
    assert "register_id" not in result["unmatched"][0]["frame"]


def test_full_identity_overrides_forged_derived_fields():
    report = inventory(
        records(frame(0x0033, 64, query=True), frame(0x0033, 64)),
        include_frame_observations=True,
    )
    report["frame_observations"][0].update(register_id=0x0033, selector_offset=0)
    result = analyze_exchanges(report)
    assert result["counts"]["pairs"] == 1
    assert result["pairs"][0]["request"]["register_id"] == "0x00400033"


@pytest.mark.parametrize(
    "identity,payload",
    [
        ("224000/0x0040051C/4", "00000000"),
        ("e24100/0x00400033/128", "0000" * 64),
        ("234000/0x00400033/0", ""),
        ("108000/0x00400033/2", "4100"),
        ("224000/0x00400033/2", "0100"),
    ],
)
def test_typed_full_id_contract_is_as_narrow_as_raw_framing(identity, payload):
    report = inventory(records(frame(0x0033, 64)), include_frame_observations=True)
    report["frame_observations"][0].update(identity=identity, payload_hex=payload)
    with pytest.raises(ValueError, match="selector-bearing"):
        analyze_exchanges(report)


def test_chunks_accept_multiframe_blocks_and_preserve_actual_completion_times():
    data = source(offsets=(0, 64))
    wire = b"".join(bytes.fromhex(row["hex"]) for row in data["frames"])
    chunks = [{"elapsed_ms": 1234, "hex": wire.hex()}]
    result = audit_metadata({"format": PAGE_FORMAT, "chunks": chunks})
    assert len(wire.hex()) > 1024
    assert len(result["rows"]) == 128
    assert all(page["delta_ms"] == 0 for page in result["pages"])
    for split in (1, 7, 11, 137, len(wire) - 1):
        split_input = [
            {"elapsed_ms": 1234, "hex": wire[:split].hex()},
            {"elapsed_ms": 1234, "hex": wire[split:].hex()},
        ]
        assert audit_metadata({"format": PAGE_FORMAT, "chunks": split_input}) == result
    fragmented = records(frame(0x0033, query=True))
    raw = frame(0x0033)
    fragmented.extend(
        [
            {"elapsed_ms": 100, "hex": raw[:12].hex()},
            {"elapsed_ms": 250, "hex": raw[12:].hex()},
        ]
    )
    assert (
        audit_metadata({"format": PAGE_FORMAT, "chunks": fragmented})["pages"][0][
            "delta_ms"
        ]
        == 250
    )


@pytest.mark.parametrize("wrapper", ["bare", "capture", "diagnostics"])
@pytest.mark.parametrize("count", [1, 64])
def test_capture_cli_uses_existing_wrappers_without_rewriting_source(
    tmp_path, monkeypatch, wrapper, count
):
    data = {"chunks": source(offsets=(0,), count=count)["frames"]}
    if wrapper == "capture":
        data = {"capture": data}
    elif wrapper == "diagnostics":
        data = {"data": {"capture": data}}
    input_path, output_path = tmp_path / "capture.json", tmp_path / "audit.json"
    original = json.dumps(data)
    input_path.write_text(original)
    monkeypatch.setattr(
        "sys.argv",
        ["audit_metadata", str(input_path), "--capture", "--output", str(output_path)],
    )
    main()
    assert len(json.loads(output_path.read_text())["rows"]) == 64
    assert input_path.read_text() == original


def test_capture_cli_rejects_state_export_without_original_chunks(
    tmp_path, monkeypatch
):
    input_path, output_path = tmp_path / "states.json", tmp_path / "audit.json"
    input_path.write_text('{"DPListe": [1, 2]}')
    monkeypatch.setattr(
        "sys.argv",
        ["audit_metadata", str(input_path), "--capture", "--output", str(output_path)],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not output_path.exists()


def test_pages_merge_identical_overlapping_last_page_and_preserve_raw_units():
    data = source()
    before = copy.deepcopy(data)
    result = audit_metadata(data)
    assert data == before
    assert len(result["rows"]) == 150
    assert result["rows"][86] == {
        "index": 86,
        "dp": "0x0056",
        "type_code": "0x0056",
        "mask_code": "0x0056",
        "unit_code": "0x0056",
    }
    assert result["required_columns_aligned_over_observed_extent"] is True
    assert result["missing_ranges"] == {f"0x{point:04X}": [] for point in POINTS}
    assert result["catalog_length"] is None
    assert "unknown" in result["catalog_completeness"]
    assert result["selector_interpretation"] == "candidate_element_offset"
    assert "°C" not in json.dumps(result)


def test_duplicate_independent_pages_merge_without_counting_more_entries():
    result = audit_metadata(source(offsets=(0, 0)))
    assert len(result["pages"]) == 8
    assert len(result["rows"]) == 64
    assert result["catalog_length"] is None


def test_identical_duplicate_reply_is_explicit_but_conflicting_reply_is_rejected():
    data = source(offsets=(0,), points=(0x0033,))
    data["frames"].append({"elapsed_ms": 20, "hex": frame(0x0033).hex()})
    assert audit_metadata(data)["duplicate_reply_frames"] == [2]
    data["frames"][-1]["hex"] = frame(0x0033, values=[7] * 64).hex()
    with pytest.raises(ValueError, match="duplicate_reply"):
        audit_metadata(data)


@pytest.mark.parametrize("point", POINTS)
def test_conflicting_overlap_fails_per_column(point):
    data = source(offsets=(0, 32))
    for row in data["frames"]:
        raw = bytes.fromhex(row["hex"])
        if (
            raw[:3] == bytes.fromhex("224000")
            and int.from_bytes(raw[3:7], "little") == (32 << 16) | point
        ):
            row["hex"] = frame(point, 32, values=[999] * 64).hex()
    with pytest.raises(ValueError, match="Conflicting metadata overlap"):
        audit_metadata(data)


def test_missing_pages_columns_and_optional_units_are_explicit():
    data = source(offsets=(0, 128), points=(0x0033, 0x0038))
    result = audit_metadata(data)
    assert len(result["rows"]) == 128
    assert result["missing_ranges"]["0x0033"] == [{"start": 64, "end": 128}]
    assert result["missing_ranges"]["0x0034"] == [{"start": 0, "end": 192}]
    assert result["missing_ranges"]["0x0039"] == [{"start": 0, "end": 192}]
    assert result["required_columns_aligned_over_observed_extent"] is False
    assert result["units_present"] is False
    assert result["rows"][0]["type_code"] is None
    assert result["rows"][0]["unit_code"] is None
    assert result["catalog_length"] is None


def test_missing_first_page_is_not_silently_shifted_to_zero():
    result = audit_metadata(source(offsets=(64,)))
    assert result["rows"][0]["index"] == 64
    assert result["missing_ranges"]["0x0033"] == [{"start": 0, "end": 64}]


def test_unanswered_query_and_late_capture_boundary_never_prove_catalog_end():
    data = source(offsets=(0,))
    data["frames"].append(
        {"elapsed_ms": 100, "hex": frame(0x0033, 64, query=True).hex()}
    )
    result = audit_metadata(data)
    assert result["unanswered_queries"] == [
        {
            "register_id": "0x00400033",
            "query_frame_index": 8,
            "reason": "end_of_capture",
        }
    ]
    assert result["catalog_length"] is None
    assert result["observed_extent"] == 64


@pytest.mark.parametrize(
    "wire,reason",
    [
        ([frame(0x0033)], "orphan_reply"),
        (
            [frame(0x0033, query=True), frame(0x0033, query=True), frame(0x0033)],
            "overlapping_request",
        ),
        ([frame(0x0033, query=True), frame(0x0033, 64)], "wrong_data_point"),
        ([frame(0x0033, query=True, header="108007")], "participant"),
        ([frame(0x0033, query=True, count=65)], "count"),
        ([frame(0x0033, query=True), frame(0x0033, values=[1, 2])], "64 uint16"),
    ],
)
def test_ambiguous_wrong_route_count_or_page_shape_are_rejected(wire, reason):
    with pytest.raises(ValueError, match=reason):
        audit_metadata({"format": PAGE_FORMAT, "frames": records(*wire)})


def test_legacy_original_fixture_output_and_input_remain_unchanged():
    replies = json.loads(
        (Path(__file__).parent / "fixtures/metadata_replies.json").read_text()
    )
    before = copy.deepcopy(replies)
    result = audit_metadata(replies)
    assert replies == before
    assert set(result) == {"framing", "semantics", "completeness", "rows"}
    assert len(result["rows"]) == 64
    assert all(set(row) == {"dp", "type_code", "mask_code"} for row in result["rows"])
    replies["0039"] = frame(0x0039, values=[8] * 64).hex()
    with_units = audit_metadata(replies)
    assert with_units["rows"][0]["unit_code"] == "0x0008"
    assert "°C" not in json.dumps(with_units)
    replies["0033"] = frame(0x0033, 64).hex()
    with pytest.raises(ValueError, match="identity"):
        audit_metadata(replies)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"format": "unknown", "frames": []},
        {"format": PAGE_FORMAT, "frames": []},
        {"format": PAGE_FORMAT, "frames": [{"elapsed_ms": 0, "hex": "bad"}]},
        {
            "format": PAGE_FORMAT,
            "frames": [{"elapsed_ms": True, "hex": frame(0x0033).hex()}],
        },
    ],
)
def test_malformed_input_rejected(value):
    with pytest.raises(ValueError):
        audit_metadata(value)
