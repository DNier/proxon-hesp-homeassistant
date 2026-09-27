"""Validate complete metadata replies offline using the existing frame inventory.

Input: JSON mapping 0033, 0034 and 0038 to complete hexadecimal response frames.
Unknown framing is rejected, not guessed. Type and mask codes remain uninterpreted.
"""

import argparse
import json
from pathlib import Path

from tools.inventory_capture import inventory


def audit_metadata(replies: dict[str, str]) -> dict:
    columns = {}
    for dp in ("0033", "0034", "0038"):
        raw = replies.get(dp)
        if not isinstance(raw, str):
            raise ValueError(f"Missing complete response for {dp}")
        frame = bytes.fromhex(raw)
        result = inventory([{"elapsed_ms": 0, "hex": frame.hex()}])
        if result["unparsed_bytes"] or result["frames"] != 1:
            raise ValueError(f"{dp}: incomplete, invalid or unsupported frame")
        group = next(iter(result["groups"].values()))
        if (
            group["header"] != "224000"
            or group["dp"] != f"0x{dp}"
            or not group["payload_bytes"]
            or group["payload_bytes"] % 2
        ):
            raise ValueError(f"{dp}: unexpected identity or payload shape")
        payload = bytes.fromhex(group["values"][0])
        columns[dp] = [
            int.from_bytes(payload[i : i + 2], "little")
            for i in range(0, len(payload), 2)
        ]
    if len({len(values) for values in columns.values()}) != 1:
        raise ValueError("Metadata columns have different lengths; cannot align rows")
    return {
        "framing": "validated_observed_nibble_length",
        "semantics": "unconfirmed_type_and_mask_codes",
        "completeness": "complete_frames_do_not_prove_complete_device_catalog",
        "rows": [
            {
                "dp": f"0x{dp:04X}",
                "type_code": f"0x{kind:04X}",
                "mask_code": f"0x{mask:04X}",
            }
            for dp, kind, mask in zip(
                columns["0033"], columns["0034"], columns["0038"], strict=True
            )
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must differ from source")
    try:
        result = audit_metadata(json.loads(args.source.read_text()))
    except (ValueError, TypeError, AttributeError) as err:
        parser.error(str(err))
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
