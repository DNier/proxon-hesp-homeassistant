"""Audit legacy metadata columns or ordered original QUERY/RESPONSE page frames.

All framing and checksums use the existing offline inventory. Page offsets are a
candidate interpretation; type, mask and unit codes remain uninterpreted.
"""

import argparse
import json
from pathlib import Path

from tools.address_analysis import analyze_exchanges
from tools.inventory_capture import METADATA_POINTS, inventory, load_capture

PAGE_FORMAT = "proxon-metadata-pages-1"
MAX_PAGE_FRAMES = 16384
MAX_INPUT_BYTES = 16 * 1024 * 1024
COLUMN_NAMES = {
    0x0033: "dp",
    0x0034: "type_code",
    0x0038: "mask_code",
    0x0039: "unit_code",
}
REQUIRED_COLUMNS = (0x0033, 0x0034, 0x0038)


def _legacy_columns(replies):
    columns = {}
    points = [*REQUIRED_COLUMNS, *([0x0039] if "0039" in replies else [])]
    for point in points:
        dp = f"{point:04X}"
        raw = replies.get(dp)
        if not isinstance(raw, str):
            raise ValueError(f"Missing complete response for {dp}")
        result = inventory([{"elapsed_ms": 0, "hex": raw}])
        if result["unparsed_bytes"] or result["frames"] != 1:
            raise ValueError(f"{dp}: incomplete, invalid or unsupported frame")
        group = next(iter(result["groups"].values()))
        if (
            group["header"] != "224000"
            or group["dp"] != f"0x{dp}"
            or group.get("selector_offset", 0)
            or not group["payload_bytes"]
            or group["payload_bytes"] % 2
        ):
            raise ValueError(f"{dp}: unexpected identity or payload shape")
        payload = bytes.fromhex(group["values"][0])
        columns[point] = [
            int.from_bytes(payload[i : i + 2], "little")
            for i in range(0, len(payload), 2)
        ]
    if len({len(values) for values in columns.values()}) != 1:
        raise ValueError("Metadata columns have different lengths; cannot align rows")
    rows = [
        {
            COLUMN_NAMES[point]: f"0x{values[index]:04X}"
            for point, values in columns.items()
        }
        for index in range(len(columns[0x0033]))
    ]
    return {
        "framing": "validated_observed_frame_shapes",
        "semantics": "unconfirmed_type_mask_and_unit_codes"
        if 0x0039 in columns
        else "unconfirmed_type_and_mask_codes",
        "completeness": "complete_frames_do_not_prove_complete_device_catalog",
        "rows": rows,
    }


def _missing_ranges(indices, extent):
    missing, cursor = [], 0
    for index in sorted(indices):
        if index > cursor:
            missing.append({"start": cursor, "end": index})
        cursor = index + 1
    if cursor < extent:
        missing.append({"start": cursor, "end": extent})
    return missing


def _paged_columns(source):
    if set(source) - {"format", "frames", "chunks", "max_response_ms"}:
        raise ValueError("Unsupported metadata page input fields")
    if ("frames" in source) == ("chunks" in source):
        raise ValueError("Metadata pages require exactly one of frames or chunks")
    framed_input = "frames" in source
    records = source.get("frames" if framed_input else "chunks")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_PAGE_FRAMES:
        raise ValueError("Metadata pages require a bounded nonempty input list")
    input_chars = 0
    for row in records:
        if (
            not isinstance(row, dict)
            or set(row) != {"elapsed_ms", "hex"}
            or not isinstance(row["hex"], str)
            or len(row["hex"]) > (1024 if framed_input else MAX_INPUT_BYTES * 2)
        ):
            raise ValueError(
                "Each metadata input frame needs elapsed_ms and original hex"
            )
        input_chars += len(row["hex"])
        if input_chars > MAX_INPUT_BYTES * 2:
            raise ValueError("Metadata input byte limit exceeded")
        if framed_input:
            result = inventory([row], include_frame_observations=True)
            if result["unparsed_bytes"] or result["frames"] != 1:
                raise ValueError(
                    "Incomplete, corrupt or unsupported original metadata input frame"
                )
    report = inventory(records, include_frame_observations=True)
    if report["unparsed_bytes"]:
        raise ValueError(
            "Capture contains incomplete, corrupt or unsupported frame bytes"
        )
    exchanges = analyze_exchanges(
        report, max_response_ms=source.get("max_response_ms", 1000)
    )
    metadata_indices = set()
    for group in report["groups"].values():
        point = int(group["dp"], 16)
        if point not in METADATA_POINTS:
            continue
        if group["header"] not in ("108000", "224000"):
            raise ValueError(
                "Metadata frame has unsupported participant or message type; "
                "expected 1 -> 2 QUERY or 2 -> 1 RESPONSE"
            )
        if group["header"] == "108000" and (
            group["payload_bytes"] != 2 or group["values"] != ["0100"]
        ):
            raise ValueError(
                "Unsupported metadata query count; "
                "only uint16 count 1 (0100) is prepared"
            )
        if group["header"] == "224000" and group["payload_bytes"] != 128:
            raise ValueError(
                "Paged metadata responses require exactly 64 uint16 entries"
            )
    for index, row in enumerate(report["frame_observations"]):
        if int(row["identity"].split("/")[1], 16) & 0xFFFF in METADATA_POINTS:
            metadata_indices.add(index)
    columns = {point: {} for point in METADATA_POINTS}
    pages, unanswered, duplicates = [], [], []
    for pair in exchanges["pairs"]:
        request, reply = pair["request"], pair["reply"]
        point = int(reply["dp"], 16)
        if point not in METADATA_POINTS:
            continue
        offset = reply.get("selector_offset", 0)
        raw = bytes.fromhex(reply["payload_hex"])
        for i in range(64):
            index, value = offset + i, int.from_bytes(raw[i * 2 : i * 2 + 2], "little")
            if index in columns[point] and columns[point][index] != value:
                raise ValueError(
                    f"Conflicting metadata overlap for 0x{point:04X} at index {index}"
                )
            columns[point][index] = value
        pages.append(
            {
                "dp": f"0x{point:04X}",
                "register_id": f"0x{(offset << 16) | point:08X}",
                "offset": offset,
                "entries": 64,
                "query_frame_index": request["frame_index"],
                "response_frame_index": reply["frame_index"],
                "delta_ms": pair["delta_ms"],
            }
        )
    for item in exchanges["unmatched"]:
        row, reason = item["frame"], item["reason"]
        if row["frame_index"] not in metadata_indices:
            continue
        if row["address"]["type"] == 0 and reason in ("timeout", "end_of_capture"):
            unanswered.append(
                {
                    "register_id": row.get(
                        "register_id", f"0x{int(row['dp'], 16):08X}"
                    ),
                    "query_frame_index": row["frame_index"],
                    "reason": reason,
                }
            )
        elif reason == "duplicate_reply" and any(
            row["identity"] == pair["reply"]["identity"]
            and row["payload_hex"] == pair["reply"]["payload_hex"]
            for pair in exchanges["pairs"]
        ):
            duplicates.append(row["frame_index"])
        else:
            raise ValueError(
                f"Unresolved metadata exchange: {reason} at frame {row['frame_index']}"
            )
    if not pages:
        raise ValueError("No unambiguous complete metadata page exchange")
    indices = set().union(*columns.values())
    extent = max(indices) + 1
    missing = {
        f"0x{point:04X}": _missing_ranges(values, extent)
        for point, values in sorted(columns.items())
    }
    return {
        "format": PAGE_FORMAT,
        "framing": "checksum_validated_candidate_metadata_pages",
        "semantics": "unconfirmed_type_mask_and_unit_codes",
        "selector_interpretation": "candidate_element_offset",
        "query_count": "0100: uint16 count 1; other counts unsupported",
        "catalog_length": None,
        "catalog_completeness": (
            "unknown; pages and unanswered queries do not prove the end of a catalog"
        ),
        "observed_extent": extent,
        "required_columns_aligned_over_observed_extent": all(
            not missing[f"0x{point:04X}"] for point in REQUIRED_COLUMNS
        ),
        "units_present": bool(columns[0x0039]),
        "missing_ranges": missing,
        "pages": pages,
        "duplicate_reply_frames": duplicates,
        "unanswered_queries": unanswered,
        "rows": [
            {
                "index": index,
                **{
                    COLUMN_NAMES[point]: f"0x{values[index]:04X}"
                    if index in values
                    else None
                    for point, values in sorted(columns.items())
                },
            }
            for index in sorted(indices)
        ],
    }


def audit_metadata(replies: dict) -> dict:
    """Preserve the legacy mapping output; page format never claims completeness."""
    if not isinstance(replies, dict):
        raise ValueError("Metadata input must be a dictionary")
    if "format" not in replies:
        return _legacy_columns(replies)
    if replies["format"] != PAGE_FORMAT:
        raise ValueError("Unsupported metadata page input format")
    return _paged_columns(replies)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Read existing chunks, capture wrapper or HA diagnostics via load_capture",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must differ from source")
    try:
        source = (
            {"format": PAGE_FORMAT, "chunks": load_capture(args.source).get("chunks")}
            if args.capture
            else json.loads(args.source.read_text())
        )
        result = audit_metadata(source)
    except (ValueError, TypeError, AttributeError) as err:
        parser.error(str(err))
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
