"""Offline payload-change inventory without a data-point or header allowlist.

Structural/checksum matches are candidates, not proof of protocol semantics.
Output can contain private raw values; keep reports outside version control.
"""

import argparse
import json
from bisect import bisect_left
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum


def inventory(chunks: list[dict]) -> dict:
    """Group by complete three-byte identity, DP and payload size.

    Uses the observed even nibble-length encoding, reserved zero bytes and
    checksum; no assumptions about unknown header identities or payload types.
    Times refer to the chunk completing a frame, not its wire transmission.
    """
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
        frames += 1
        timestamp = times[bisect_left(ends, pos)]
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
                "last_seen_ms": timestamp,
                "values": [],
                "changes": [],
            },
        )
        raw = frame[8:-2].hex()
        item["count"] += 1
        item["last_seen_ms"] = timestamp
        if raw not in item["values"]:
            item["values"].append(raw)
        if not item["changes"] or item["changes"][-1]["payload_hex"] != raw:
            item["changes"].append({"elapsed_ms": timestamp, "payload_hex": raw})
    return {
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for index, path in enumerate(args.captures, 1):
        capture = json.loads(path.read_text())["data"]["capture"]
        results.append({"capture_index": index, **inventory(capture["chunks"])})
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
