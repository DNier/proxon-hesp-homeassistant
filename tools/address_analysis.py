"""Candidate HESP address fields and exchanges from validated inventory rows.

This module never parses, generates or transmits wire frames. Candidate fields
and temporal pairs do not identify hardware roles or establish command acceptance.
"""

import heapq
import re
from collections import Counter

from tools.frame_observations import frames, integer

TYPE_NAMES = {0: "query", 1: "set", 2: "response", 3: "confirm"}
_TYPE_COUNT_NAMES = (*TYPE_NAMES.values(), "unknown")


def decode_header(header: str) -> dict:
    """Split a three-byte little-endian header using the candidate bit layout."""
    if not isinstance(header, str) or re.fullmatch(r"[0-9a-fA-F]{6}", header) is None:
        raise ValueError("header must contain exactly three hexadecimal bytes")
    value = int.from_bytes(bytes.fromhex(header), "little")
    type_code = value & 15
    return {
        "header_le24": value,
        "type": type_code,
        "type_name": TYPE_NAMES.get(type_code, "unknown"),
        "source": (value >> 4) & 1023,
        "destination": (value >> 14) & 1023,
    }


def _record(row):
    return {
        "identity": row["identity"],
        "header": row["header"],
        "dp": f"0x{row['dp']:04X}",
        "payload_bytes": row["payload_bytes"],
        "payload_hex": row["payload_hex"],
        "elapsed_ms": row["elapsed_ms"],
        "frame_index": row["frame_index"],
        "unparsed_bytes_before": row["unparsed_bytes_before"],
        "address": decode_header(row["header"]),
    }


class _Matcher:
    """Conservative per-key pending requests and ambiguity quarantine."""

    def __init__(self, max_response_ms):
        self.max_response_ms = max_response_ms
        self.pending = {}
        self.quarantine = {}
        self.history = {}
        self.deadlines = []
        self.pending_routes = Counter()
        self.pending_points = Counter()
        self.pairs = []
        self.unmatched = []

    def _unmatched(self, frame, reason):
        self.unmatched.append({"reason": reason, "frame": frame})

    def _remove_pending(self, key):
        frame = self.pending.pop(key)
        self.pending_routes[key[:3]] -= 1
        self.pending_points[(key[0], key[3])] -= 1
        return frame

    def _block(self, key, deadline, reason):
        self.quarantine[key] = (deadline, reason)
        heapq.heappush(self.deadlines, (deadline, key))

    def advance(self, now):
        # Inclusive response bound: at the exact deadline a request or its
        # quarantine is still active. Zero therefore supports same-TCP-time pairs.
        while self.deadlines and self.deadlines[0][0] < now:
            deadline, key = heapq.heappop(self.deadlines)
            request = self.pending.get(key)
            if (
                request is not None
                and request["elapsed_ms"] + self.max_response_ms == deadline
            ):
                self._unmatched(self._remove_pending(key), "timeout")
                self.history[key]["status"] = "timeout"
            blocked = self.quarantine.get(key)
            if blocked is not None and blocked[0] == deadline:
                del self.quarantine[key]

    def break_continuity(self):
        for key in list(self.pending):
            request = self._remove_pending(key)
            self._unmatched(request, "continuity_break")
            self.history[key]["status"] = "continuity_break"
            self._block(
                key,
                request["elapsed_ms"] + self.max_response_ms,
                "continuity_break",
            )

    def request(self, key, frame):
        deadline = frame["elapsed_ms"] + self.max_response_ms
        if key in self.pending or key in self.quarantine:
            if key in self.pending:
                self._unmatched(self._remove_pending(key), "overlapping_request")
            self._unmatched(frame, "overlapping_request")
            self.history[key] = {"request": frame, "status": "overlapping_request"}
            self._block(key, deadline, "ambiguous_reply")
            return
        self.pending[key] = frame
        self.history[key] = {"request": frame, "status": "pending"}
        self.pending_routes[key[:3]] += 1
        self.pending_points[(key[0], key[3])] += 1
        heapq.heappush(self.deadlines, (deadline, key))

    def reply(self, key, frame):
        if key in self.quarantine:
            self._unmatched(frame, self.quarantine[key][1])
            return
        if key in self.pending:
            request = self._remove_pending(key)
            delta = frame["elapsed_ms"] - request["elapsed_ms"]
            self.pairs.append(
                {
                    "kind": "query_response" if key[0] == 0 else "set_confirm",
                    "classification": "candidate",
                    "request": request,
                    "reply": frame,
                    "delta_ms": delta,
                    "same_tcp_timestamp": delta == 0,
                }
            )
            self.history[key]["status"] = "paired"
            return
        old = self.history.get(key)
        if old is not None:
            delta = frame["elapsed_ms"] - old["request"]["elapsed_ms"]
            if delta > self.max_response_ms:
                reason = "late_reply"
            elif old["status"] == "paired":
                reason = "duplicate_reply"
            else:
                reason = "orphan_reply"
        elif (1 - key[0], *key[1:]) in self.pending:
            reason = "wrong_reply_type"
        elif self.pending_routes[key[:3]]:
            reason = "wrong_data_point"
        elif self.pending_points[(key[0], key[3])]:
            reason = "wrong_endpoints"
        else:
            reason = "orphan_reply"
        self._unmatched(frame, reason)

    def finish(self, coverage_end, end_reason):
        self.advance(coverage_end)
        for key in list(self.pending):
            self._unmatched(self._remove_pending(key), end_reason)


def analyze_exchanges(report: dict, *, max_response_ms: int = 1000) -> dict:
    """Correlate reversed-endpoint QUERY/RESPONSE and SET/CONFIRM candidates.

    All timing, framing, checksum validation and window selection come from the
    inventory. Payload sizes may differ. Lost observation continuity or same-key
    overlapping requests must never select a convenient request for a reply.
    """
    integer(max_response_ms, "max_response_ms")
    if not isinstance(report, dict):
        raise ValueError("inventory report must be a dictionary")
    window = report.get("window")
    if not isinstance(window, dict):
        raise ValueError("inventory window is required")
    start = integer(window.get("start_ms"), "window start_ms")
    end = window.get("end_ms")
    if end is not None:
        integer(end, "window end_ms", minimum=start + 1)
    capture_end = integer(report.get("last_chunk_ms"), "last_chunk_ms")
    matcher = _Matcher(max_response_ms)
    participants, routes = {}, {}
    counts = dict.fromkeys(_TYPE_COUNT_NAMES, 0)
    unknown_frames, continuity_breaks = [], []
    previous = None
    for row in frames(report):
        now = row["elapsed_ms"]
        if now < start or (end is not None and now >= end):
            raise ValueError("frame observation outside selected window")
        if now > capture_end:
            raise ValueError("frame observation outside capture")
        matcher.advance(now)
        reasons = []
        if previous is not None:
            if row["frame_index"] != previous["frame_index"] + 1:
                reasons.append("frame_index_gap")
            if row["unparsed_bytes_before"] != previous["unparsed_bytes_before"]:
                reasons.append("unparsed_bytes")
        if reasons:
            matcher.break_continuity()
            continuity_breaks.append(
                {
                    "before_frame_index": previous["frame_index"],
                    "after_frame_index": row["frame_index"],
                    "elapsed_ms": now,
                    "reasons": reasons,
                }
            )
        frame = _record(row)
        address = frame["address"]
        source, destination = address["source"], address["destination"]
        name, type_code = address["type_name"], address["type"]
        counts[name] += 1
        for participant in (source, destination):
            participants.setdefault(
                participant, {"address": participant, "sent": 0, "received": 0}
            )
        participants[source]["sent"] += 1
        participants[destination]["received"] += 1
        route = routes.setdefault(
            (source, destination),
            {
                "source": source,
                "destination": destination,
                "count": 0,
                "type_counts": dict.fromkeys(_TYPE_COUNT_NAMES, 0),
            },
        )
        route["count"] += 1
        route["type_counts"][name] += 1
        if type_code in (0, 1):
            matcher.request((type_code, source, destination, row["dp"]), frame)
        elif type_code in (2, 3):
            matcher.reply((type_code - 2, destination, source, row["dp"]), frame)
        else:
            unknown_frames.append(frame)
        previous = row
    matcher.finish(
        min(capture_end, end) if end is not None else capture_end,
        "end_of_window" if end is not None else "end_of_capture",
    )
    pairs = sorted(matcher.pairs, key=lambda pair: pair["request"]["frame_index"])
    unmatched = sorted(matcher.unmatched, key=lambda item: item["frame"]["frame_index"])
    return {
        "classification": (
            "Candidate address fields and request/reply correlations only"
        ),
        "header_layout": (
            "H=LE24; type=H&15; source=(H>>4)&1023; destination=(H>>14)&1023"
        ),
        "time_basis": (
            "TCP chunk completing frame, not electrical bus transmission time"
        ),
        "window": {"start_ms": start, "end_ms": end},
        "max_response_ms": max_response_ms,
        "counts": {
            "frames": sum(counts.values()),
            **counts,
            "pairs": len(pairs),
            "unmatched": len(unmatched),
        },
        "participants": [participants[key] for key in sorted(participants)],
        "routes": [routes[key] for key in sorted(routes)],
        "pairs": pairs,
        "unmatched": unmatched,
        "unknown_frames": unknown_frames,
        "continuity_breaks": continuity_breaks,
        "caution": (
            "Candidate fields do not identify hardware roles. A pair does not prove "
            "an accepted command, actuator state or payload meaning. Reply delay is "
            "an inclusive analysis bound, not a measured protocol guarantee. Equal "
            "TCP timestamps preserve frame order but do not establish zero bus "
            "latency. Same-key overlaps remain quarantined through the latest "
            "request's deadline. Skipped bytes or frame indexes break continuity. "
            "Nothing is paired across selected windows or separate captures."
        ),
    }
