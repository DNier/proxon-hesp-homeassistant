"""Offline validation of frozen checksum against recorded frame candidates.

No fitting, no equipment connection, and no raw traffic in the report.
Scanning is deliberately limited to observed node/type headers and even
nibble lengths. Counts do not claim to cover every byte of a capture.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.analyze_temperature_checksum import read

HEADERS = tuple(bytes.fromhex(h) for h in ("108000", "118000", "224000", "234000"))


def candidates(data):
    for offset in range(max(0, len(data) - 9)):
        header = data[offset : offset + 8]
        if header[:3] not in HEADERS or header[5:7] != b"\0\0" or header[7] % 2:
            continue
        length = 10 + header[7] // 2
        frame = data[offset : offset + length]
        if len(frame) == length:
            yield frame


def validate(data):
    counts = Counter()
    unique = set()
    for frame in candidates(data):
        predicted = checksum(frame[:-2])
        status = (
            "unsupported"
            if predicted is None
            else "match"
            if predicted == int.from_bytes(frame[-2:], "little")
            else "mismatch"
        )
        counts[len(frame) - 10, status] += 1
        unique.add(frame)
    return {
        "frames": sum(counts.values()),
        "unique_frames": len(unique),
        "by_payload_size": [
            {"bytes": size, "status": status, "count": count}
            for (size, status), count in sorted(counts.items())
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(
            [
                {"capture_index": i, **validate(read(path))}
                for i, path in enumerate(args.captures, 1)
            ],
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
