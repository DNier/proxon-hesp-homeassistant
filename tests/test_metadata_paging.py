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


def source(offsets=(0, 64, 86), points=POINTS):
    wire = []
    for offset in offsets:
        for point in points:
            wire.extend((frame(point, offset, query=True), frame(point, offset)))
    return {"format": PAGE_FORMAT, "frames": records(*wire)}


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
        frame(0x0033, 64, query=True, count=64),
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


def test_address_matcher_uses_the_whole_register_id_when_pages_interleave():
    report = inventory(
        records(
            frame(0x0033, query=True),
            frame(0x0033, 64, query=True),
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
        ("108000/0x00400033/2", "4000"),
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
def test_capture_cli_uses_existing_wrappers_without_rewriting_source(
    tmp_path, monkeypatch, wrapper
):
    data = {"chunks": source(offsets=(0,))["frames"]}
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
        ([frame(0x0033, query=True, count=64)], "count"),
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
