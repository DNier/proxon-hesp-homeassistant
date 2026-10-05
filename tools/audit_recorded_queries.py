"""Offline QUERY/response-shape observations in one selected recording.

Co-occurrence does not pair requests with replies or establish causation,
semantics, freshness, or permission to transmit. Reports remain private.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.analyze_temperature_checksum import read
from tools.inventory_capture import inventory as capture_inventory
from tools.inventory_capture import load_capture

# Recorded (request argument, response payload bytes), not a conversion rule.
# The same argument can describe different lengths; no payload type is inferred.
# These shapes cover the observed 108000 queries and 224000 controller replies.
OBSERVED_RESPONSE_SHAPES = {
    0x006C: (1, 4),
    0x00C9: (2, 8),
    0x00D2: (4, 16),
    0x00D3: (4, 16),
    0x00D7: (2, 8),
    0x00ED: (1, 4),
    0x00EE: (1, 4),
    0x0105: (1, 4),
    0x0110: (1, 4),
    0x0115: (1, 4),
    0x0116: (2, 4),
    0x011C: (1, 4),
    0x0120: (1, 2),
    0x0123: (1, 2),
    0x0160: (1, 1),
    0x0168: (1, 1),
    0x0178: (6, 12),
    0x01F5: (1, 4),
    0x0206: (1, 2),
    0x0208: (1, 4),
    0x020F: (1, 2),
    0x02D0: (1, 4),
    0x02D1: (1, 4),
    0x02D2: (1, 4),
    0x02D3: (1, 4),
    0x02D4: (1, 4),
    0x02D5: (1, 4),
    0x02D6: (20, 40),
    0x02D7: (1, 4),
    0x02D9: (1, 4),
    0x02DF: (28, 112),
    0x032E: (2, 4),
    0x0330: (0, 4),
    0x03B7: (11, 22),
    0x0519: (1, 2),
    0x051C: (1, 4),
    0x051D: (2, 4),
    0x051E: (2, 4),
}


def inventory(data: bytes) -> list[dict]:
    """Retain the legacy byte-scan candidate report, including bad checksums.

    Unlike audit(), this helper does not establish supported frame boundaries.
    """
    counts = Counter()
    for offset in range(max(0, len(data) - 11)):
        frame = data[offset : offset + 12]
        if frame[:3] != b"\x10\x80\x00" or frame[5:8] != b"\x00\x00\x04":
            continue
        calculated = checksum(frame[:-2])
        status = (
            "unsupported"
            if calculated is None
            else "match"
            if calculated == int.from_bytes(frame[-2:], "little")
            else "mismatch"
        )
        counts[(frame.hex(), status)] += 1
    return [
        {
            "dp": f"0x{int.from_bytes(bytes.fromhex(frame)[3:5], 'little'):04X}",
            "request_argument": int.from_bytes(bytes.fromhex(frame)[8:10], "little"),
            "frame": frame,
            "checksum": status,
            "occurrences": count,
        }
        for (frame, status), count in sorted(counts.items())
    ]


def _observation(identity: str, group: dict) -> dict:
    return {
        "identity": identity,
        "count": group["count"],
        "first_seen_ms": group["first_seen_ms"],
        "last_seen_ms": group["last_seen_ms"],
    }


def audit(capture: dict) -> dict:
    """Compare exact recorded shapes without inferring temporal associations.

    Only queries at valid boundaries from the existing inventory parser qualify.
    A response may precede a query, repeat, or be absent in the selected capture;
    counts must not be read as one-to-one request/response associations.
    """
    overview = capture_inventory(capture["chunks"])
    groups = overview["groups"]
    queries = []
    for identity, group in groups.items():
        if group["header"] != "108000" or group["payload_bytes"] != 2:
            continue
        dp = int(group["dp"], 16)
        shape = OBSERVED_RESPONSE_SHAPES.get(dp)
        for payload, count in sorted(group["payload_counts"].items()):
            argument = int.from_bytes(bytes.fromhex(payload), "little")
            expected = (
                f"224000/{group['dp']}/{shape[1]}"
                if shape is not None and argument == shape[0]
                else None
            )
            response = groups.get(expected) if expected is not None else None
            queries.append(
                {
                    "identity": identity,
                    "dp": group["dp"],
                    "request_argument": argument,
                    "occurrences": count,
                    "expected_response_identity": expected,
                    "response_status": (
                        "unsupported_query_shape"
                        if expected is None
                        else "observed"
                        if response is not None
                        else "not_observed"
                    ),
                    "response_observation": (
                        _observation(expected, response)
                        if response is not None
                        else None
                    ),
                    "other_same_dp_groups": [
                        _observation(key, item)
                        for key, item in groups.items()
                        if item["dp"] == group["dp"]
                        and item["header"] != "108000"
                        and key != expected
                    ],
                }
            )
    return {
        "association_basis": (
            "Co-occurrence within the selected recording only; no causal or "
            "one-to-one request/reply association, semantics or freshness claim."
        ),
        "overview": {key: value for key, value in overview.items() if key != "groups"},
        "queries": queries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--capture", choices=("manual", "event"), default="manual")
    parser.add_argument(
        "--event-index",
        type=int,
        help="Event index: 0 oldest, -1 latest (default); requires --capture event",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.event_index is not None and args.capture != "event":
        parser.error("--event-index requires --capture event")
    if args.output.resolve() == args.input.resolve():
        parser.error("output must differ from input")
    if args.input.suffix != ".json" and args.capture == "event":
        parser.error("event selection requires a JSON capture")
    event_index = args.event_index if args.event_index is not None else -1
    try:
        if args.input.suffix != ".json":
            # Preserve the untimed legacy byte report; do not fabricate chunks.
            report = inventory(read(args.input))
        else:
            capture = load_capture(
                args.input, event=args.capture == "event", event_index=event_index
            )
            report = {
                "selected_capture": args.capture,
                "event_index": event_index if args.capture == "event" else None,
                **audit(capture),
            }
    except (OSError, KeyError, TypeError, ValueError) as err:
        parser.error(str(err))
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
