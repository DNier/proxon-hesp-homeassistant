"""Offline inventory of exact controller QUERY candidates in a diagnosis."""

import argparse
import json
from collections import Counter
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.analyze_temperature_checksum import read


def inventory(data: bytes) -> list[dict]:
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inventory(read(args.capture)), indent=2) + "\n")


if __name__ == "__main__":
    main()
