"""Offline audit of recorded BDE SETs and subsequent same-DP empty ACKs.

No transmitter. ACK association is temporal evidence, not proof of acceptance,
persistence, or permission to introduce an additional bus master.
"""

import argparse
import json
import math
import struct
from bisect import bisect_left
from collections import Counter
from pathlib import Path

from custom_components.proxon_hesp.hesp.checksum import checksum

HEADERS = {
    bytes.fromhex(header)
    for header in (
        "108000",
        "118000",
        "224000",
        "234000",
        "108007",
        "118007",
        "e24100",
        "e34100",
    )
}
POINTS = {
    0x00E1: ("panel_requested_fan_level", 2),
    0x01F8: ("panel_flags", 4),
    0x020A: ("operating_mode", 2),
    0x0227: ("target_temperature", 4),
}


def _value(dp: int, payload: bytes):
    if dp == 0x0227:
        value = struct.unpack("<f", payload)[0]
        return value if math.isfinite(value) else None
    return int.from_bytes(payload, "little")


def audit(chunks: list[dict], ack_window_ms: int = 1000) -> dict:
    """Count exact observed headers; timestamps mark frame-completing chunks.

    With two pending SETs for the same DP an ACK is deliberately ambiguous.
    Zero milliseconds means same capture timestamp, not zero wire latency.
    Unknown, corrupt, and truncated bytes are reported as unparsed.
    """
    if ack_window_ms <= 0:
        raise ValueError("ack_window_ms must be positive")
    data = bytearray()
    ends, times = [], []
    for chunk in chunks:
        timestamp = chunk["elapsed_ms"]
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("elapsed_ms must be a nonnegative integer")
        if times and timestamp < times[-1]:
            raise ValueError("capture timestamps must be monotonic")
        data.extend(bytes.fromhex(chunk["hex"]))
        ends.append(len(data))
        times.append(timestamp)

    points = {}
    pending = {}
    last_time = {}
    delays = {}
    intervals = {}
    frame_counts = Counter()
    pos = parsed = 0
    malformed_selected = 0
    while pos + 10 <= len(data):
        header = bytes(data[pos : pos + 8])
        size = header[7] // 2
        length = 10 + size
        frame = bytes(data[pos : pos + length])
        if (
            header[:3] not in HEADERS
            or header[5:7] != b"\0\0"
            or header[7] % 2
            or size > 112
            or len(frame) != length
            or checksum(frame[:-2]) != int.from_bytes(frame[-2:], "little")
        ):
            pos += 1
            continue
        pos += length
        parsed += length
        frame_counts[header[:3].hex()] += 1
        timestamp = times[bisect_left(ends, pos)]
        dp = int.from_bytes(header[3:5], "little")
        if dp not in POINTS:
            continue
        is_set = header[:3] == b"\x11\x80\x00"
        is_ack = header[:3] == b"\x23\x40\x00" and size == 0
        if not is_set and not is_ack:
            continue
        name, expected_size = POINTS[dp]
        if is_set and size != expected_size:
            malformed_selected += 1
            continue
        item = points.setdefault(
            dp,
            {
                "name": name,
                "sets": 0,
                "value_changes": 0,
                "unchanged_repeats": 0,
                "ack_associations": 0,
                "ambiguous_acks": 0,
                "sets_with_ambiguous_ack": 0,
                "sets_without_ack_in_window": 0,
                "acks_without_pending_set": 0,
                "values": [],
                "changes": [],
            },
        )
        queue = pending.setdefault(dp, [])
        expired = [t for t in queue if timestamp - t > ack_window_ms]
        item["sets_without_ack_in_window"] += len(expired)
        queue[:] = [t for t in queue if timestamp - t <= ack_window_ms]
        if is_set:
            payload = frame[8:-2]
            raw = payload.hex()
            item["sets"] += 1
            if dp in last_time:
                intervals.setdefault(dp, []).append(timestamp - last_time[dp])
            last_time[dp] = timestamp
            if not item["changes"] or item["changes"][-1]["payload_hex"] != raw:
                if item["changes"]:
                    item["value_changes"] += 1
                item["changes"].append(
                    {
                        "elapsed_ms": timestamp,
                        "payload_hex": raw,
                        "value": _value(dp, payload),
                    }
                )
            else:
                item["unchanged_repeats"] += 1
            if raw not in item["values"]:
                item["values"].append(raw)
            queue.append(timestamp)
        elif len(queue) == 1:
            item["ack_associations"] += 1
            delays.setdefault(dp, []).append(timestamp - queue[0])
            queue.clear()
        elif queue:
            item["ambiguous_acks"] += 1
            item["sets_with_ambiguous_ack"] += len(queue)
            queue.clear()
        else:
            item["acks_without_pending_set"] += 1

    end_ms = times[-1] if times else 0
    for dp, item in points.items():
        # Capture ending early cannot establish a missing ACK.
        item["sets_pending_at_capture_end"] = sum(
            end_ms - t <= ack_window_ms for t in pending[dp]
        )
        item["sets_without_ack_in_window"] += sum(
            end_ms - t > ack_window_ms for t in pending[dp]
        )
        for key, values in (
            ("ack_capture_delta_ms", delays.get(dp, [])),
            ("set_interval_ms", intervals.get(dp, [])),
        ):
            item[key] = {"min": min(values), "max": max(values)} if values else None
    return {
        "bytes": len(data),
        "parsed_bytes": parsed,
        "unparsed_bytes": len(data) - parsed,
        "frame_counts_by_header": dict(sorted(frame_counts.items())),
        "last_chunk_ms": end_ms,
        "ack_window_ms": ack_window_ms,
        "malformed_selected_sets": malformed_selected,
        "points": {f"0x{dp:04X}": item for dp, item in sorted(points.items())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ack-window-ms", type=int, default=1000)
    args = parser.parse_args()
    results = []
    for index, path in enumerate(args.captures, 1):
        capture = json.loads(path.read_text())["data"]["capture"]
        results.append(
            {
                "capture_index": index,
                **audit(capture["chunks"], args.ack_window_ms),
            }
        )
    args.output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
