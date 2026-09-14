"""Prepare offline query candidates. This module has no network transport."""

import argparse
import json
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum

# Response size for metadata arrays is not established; do not guess a count.
TEMPERATURES = {
    0x0194: "T1 Zuluft",
    0x0231: "T3 Frischluft",
    0x0230: "T4 Fortluft",
    0x0190: "T5 vor Verdampfer",
    0x0191: "T6 Verdampfer",
    0x022E: "T7 Abluft",
    0x0192: "T8 nach Vorwaerme",
    0x022D: "T10 Kondensator",
    0x0193: "T12 vor Kondensator",
    0x0195: "T13 Kompressor",
}
METADATA = {
    0x0001: "Node-Name",
    0x0033: "DP-Verzeichnis",
    0x0034: "Typcodes",
    0x0038: "Zugriffsmaske",
    0x0039: "Einheiten",
}


def query_candidate(dp: int) -> bytes:
    """Fixed QUERY identity; single-element temperature request is unvalidated."""
    if dp not in TEMPERATURES:
        raise ValueError("Only allowlisted temperature points can be prepared")
    message = b"\x10\x80\x00" + dp.to_bytes(2, "little")
    message += b"\x00\x00\x04\x01\x00"
    crc = checksum(message)
    if crc is None:
        raise ValueError("Query is outside the checksum model")
    return message + crc.to_bytes(2, "little")


def plan() -> dict:
    candidates = []
    for dp, name in TEMPERATURES.items():
        try:
            frame = query_candidate(dp).hex()
            status = "candidate_not_validated_on_device"
        except ValueError:
            frame = None
            status = "checksum_unsupported"
        candidates.append(
            {"dp": f"0x{dp:04X}", "name": name, "frame": frame, "status": status}
        )
    return {
        "offline_only": True,
        "transmission_enabled": False,
        "request_count_hypothesis": "0100: one element, unvalidated",
        "temperature_candidates": candidates,
        "metadata": [
            {
                "dp": f"0x{dp:04X}",
                "name": name,
                "status": "request_length_and_response_framing_unresolved",
            }
            for dp, name in METADATA.items()
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(plan(), indent=2) + "\n")


if __name__ == "__main__":
    main()
