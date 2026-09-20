"""Offline payload-change inventory without a data-point or header allowlist.

Structural/checksum matches are candidates, not proof of protocol semantics.
Output can contain private raw values; keep reports outside version control.
"""

import argparse
import json
from bisect import bisect_left
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum


def load_capture(path: Path, *, event: bool = False) -> dict:
    """Read HA diagnostics, a capture wrapper or a bare capture."""
    data = json.loads(path.read_text())
    if event:
        return data.get("data", data)["event_capture"]
    return data.get("data", data).get("capture", data)


def inventory(
    chunks: list[dict], *, start_ms: int = 0, end_ms: int | None = None
) -> dict:
    """Group by complete three-byte identity, DP and payload size.

    Uses the observed even nibble-length encoding, reserved zero bytes and
    checksum; no assumptions about unknown header identities or payload types.
    Times refer to the chunk completing a frame, not its wire transmission.
    """
    if type(start_ms) is not int or start_ms < 0:
        raise ValueError("start_ms must be a nonnegative integer")
    if end_ms is not None and (type(end_ms) is not int or end_ms <= start_ms):
        raise ValueError("end_ms must be an integer greater than start_ms")
    data = bytearray()
    ends, times = [], []
    for chunk in chunks:
        timestamp = chunk["elapsed_ms"]
        if type(timestamp) is not int or timestamp < 0:
            raise ValueError("elapsed_ms must be a nonnegative integer")
        if times and timestamp < times[-1]:
            raise ValueError("capture timestamps must be monotonic")
        data.extend(bytes.fromhex(chunk["hex"]))
        ends.append(len(data))
        times.append(timestamp)

    groups = {}
    pos = parsed = frames = 0
    while pos + 10 <= len(data):
        header = data[pos : pos + 8]
        size = header[7] // 2
        length = 10 + size
        frame = data[pos : pos + length]
        if (
            header[5:7] != b"\0\0"
            or header[7] % 2
            or size > 112
            or len(frame) != length
            or checksum(frame[:-2]) != int.from_bytes(frame[-2:], "little")
        ):
            pos += 1
            continue
        pos += length
        parsed += length
        timestamp = times[bisect_left(ends, pos)]
        if timestamp < start_ms or (end_ms is not None and timestamp >= end_ms):
            continue
        frames += 1
        identity = header[:3].hex()
        dp = int.from_bytes(header[3:5], "little")
        key = f"{identity}/0x{dp:04X}/{size}"
        item = groups.setdefault(
            key,
            {
                "header": identity,
                "dp": f"0x{dp:04X}",
                "payload_bytes": size,
                "count": 0,
                "first_seen_ms": timestamp,
                "last_seen_ms": timestamp,
                "payload_counts": {},
                "values": [],
                "changes": [],
            },
        )
        raw = frame[8:-2].hex()
        item["count"] += 1
        item["payload_counts"][raw] = item["payload_counts"].get(raw, 0) + 1
        item["last_seen_ms"] = timestamp
        if raw not in item["values"]:
            item["values"].append(raw)
        if not item["changes"] or item["changes"][-1]["payload_hex"] != raw:
            item["changes"].append({"elapsed_ms": timestamp, "payload_hex": raw})
    return {
        "window": {"start_ms": start_ms, "end_ms": end_ms},
        "byte_coverage_scope": "whole_capture",
        "max_chunk_gap_ms": max(
            (b - a for a, b in zip(times, times[1:], strict=False)), default=0
        ),
        "bytes": len(data),
        "parsed_bytes": parsed,
        "unparsed_bytes": len(data) - parsed,
        "frames": frames,
        "last_chunk_ms": times[-1] if times else 0,
        "groups": dict(sorted(groups.items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument(
        "--event", action="store_true", help="Use automatic event capture"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for index, path in enumerate(args.captures, 1):
        capture = load_capture(path, event=args.event)
        results.append({"capture_index": index, **inventory(capture["chunks"])})
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
