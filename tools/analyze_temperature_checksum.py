"""Offline GF(2) identifiability check; never connects to equipment.

Training and validation inputs must be distinct captures. A dependent prediction
is evidence only within the observed bit subspace, not a general checksum.
"""

import argparse
import json
from pathlib import Path

HEADER = bytes.fromhex("224000b70300002c")


def read(path):
    if path.suffix != ".json":
        return path.read_bytes()
    data = json.loads(path.read_text())
    capture = data.get("data", data).get("capture", data)
    return b"".join(bytes.fromhex(chunk["hex"]) for chunk in capture["chunks"])


def frames(data):
    result = []
    offset = 0
    while (offset := data.find(HEADER, offset)) >= 0:
        frame = data[offset : offset + 32]
        if len(frame) == 32:
            result.append(frame)
        offset += 1
    return result


def vector(frame):
    # Include an affine intercept; do not assume it is zero.
    return int.from_bytes(frame[:-2], "little") | (1 << 240)


def reduce(row, crc, basis):
    while row:
        pivot = row.bit_length() - 1
        if pivot not in basis:
            break
        x, y = basis[pivot]
        row ^= x
        crc ^= y
    return row, crc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("training", type=Path)
    parser.add_argument("validation", type=Path)
    args = parser.parse_args()
    training, validation = frames(read(args.training)), frames(read(args.validation))
    basis = {}
    conflicts = 0
    for frame in training:
        row, crc = reduce(vector(frame), int.from_bytes(frame[-2:], "little"), basis)
        if row:
            basis[row.bit_length() - 1] = row, crc
        elif crc:
            conflicts += 1
    outcomes = {"predicted_match": 0, "predicted_mismatch": 0, "not_identifiable": 0}
    for frame in validation:
        row, crc = reduce(vector(frame), int.from_bytes(frame[-2:], "little"), basis)
        key = (
            "not_identifiable"
            if row
            else "predicted_mismatch"
            if crc
            else "predicted_match"
        )
        outcomes[key] += 1
    varied = 0
    if training:
        for frame in training:
            varied |= vector(frame) ^ vector(training[0])
    print(
        json.dumps(
            {
                "training_frames": len(training),
                "training_unique": len(set(training)),
                "rank": len(basis),
                "training_conflicts": conflicts,
                "varying_input_bits": varied.bit_count(),
                "validation_frames": len(validation),
                "validation_unique": len(set(validation)),
                **outcomes,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
