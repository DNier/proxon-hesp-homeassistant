"""Replay local diagnostics through production decoder without network access."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from custom_components.proxon_hesp.hesp.decoder import Decoder
from tools.analyze_temperature_checksum import read
from tools.inventory_capture import load_capture


def replay(data: bytes, chunk_size: int = 127) -> dict:
    """Bound output by supported sensor keys; do not export raw traffic."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    decoder = Decoder()
    readings = {}
    for offset in range(0, len(data), chunk_size):
        for reading in decoder.feed(data[offset : offset + chunk_size]):
            item = readings.setdefault(
                reading.key,
                {"count": 0, "first": reading.value, "last": reading.value},
            )
            item["count"] += 1
            item["last"] = reading.value
    return {"statistics": asdict(decoder.stats), "readings": readings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument(
        "--event", action="store_true", help="Use automatic event capture"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def source(path):
        if args.event:
            return b"".join(
                bytes.fromhex(c["hex"])
                for c in load_capture(path, event=True)["chunks"]
            )
        return read(path)

    # Index sources instead of copying private absolute file paths or entry IDs.
    results = [
        {"capture_index": i, **replay(source(path))}
        for i, path in enumerate(args.captures, 1)
    ]
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
