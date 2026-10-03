"""Compare candidate fan curves with raw control pairs, strictly offline.

JSON input: complete response frames in keys 00d2 and 00d3, plus a list of
complete 00d7 response frames in observations. No actual operating level, physical
unit or synchronized state is inferred from a numerical match.
"""

import argparse
import json
import math
import struct
from pathlib import Path

from tools.inventory_capture import inventory


def _payload(raw: str, dp: str, size: int) -> bytes:
    if not isinstance(raw, str):
        raise ValueError(f"{dp}: expected a complete hexadecimal response")
    result = inventory([{"elapsed_ms": 0, "hex": raw}])
    key = f"224000/0x{dp.upper()}/{size}"
    if result["unparsed_bytes"] or result["frames"] != 1 or key not in result["groups"]:
        raise ValueError(f"{dp}: invalid identity, length or checksum")
    return bytes.fromhex(result["groups"][key]["values"][0])


def audit_fan_curves(data: dict) -> dict:
    """Return candidate positions using the observed factor 100 hypothesis."""
    curves = {}
    for dp in ("00d2", "00d3"):
        values = struct.unpack("<4f", _payload(data.get(dp), dp, 16))
        if any(not math.isfinite(v) or not 0 <= v <= 100 for v in values):
            raise ValueError(f"{dp}: outside candidate curve range 0..100")
        curves[dp] = values
    observations = data.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("Expected a nonempty list of observations")
    matches = []
    for index, raw in enumerate(observations):
        pair = struct.unpack("<2f", _payload(raw, "00d7", 8))
        if any(not math.isfinite(v) or not 0 <= v <= 10000 for v in pair):
            raise ValueError("00d7: invalid raw control pair")
        per_channel = [
            [
                i + 1
                for i, value in enumerate(curves[dp])
                # Allow float32 representation error, not a physical deadband.
                if math.isclose(value * 100, pair[channel], rel_tol=1e-6, abs_tol=0.001)
            ]
            for channel, dp in enumerate(("00d2", "00d3"))
        ]
        common = sorted(set(per_channel[0]) & set(per_channel[1]))
        matches.append(
            {
                "observation_index": index,
                "raw_pair": pair,
                "channel_candidate_positions": per_channel,
                "common_candidate_positions": common,
                "result": "unique_match"
                if len(common) == 1
                else "ambiguous_match"
                if common
                else "no_common_match",
            }
        )
    return {
        "semantics": "numerical_candidates_not_actual_fan_levels",
        "assumption": "00d2_to_channel_0_00d3_to_channel_1_factor_100",
        "timing": "input_frames_not_assumed_simultaneous_or_current",
        "curves": curves,
        "observations": matches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must differ from source")
    try:
        result = audit_fan_curves(json.loads(args.source.read_text()))
    except (ValueError, TypeError, AttributeError) as err:
        parser.error(str(err))
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
