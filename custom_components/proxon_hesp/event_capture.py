"""Opt-in, bounded recording of validated readings and undecoded bit edges."""

import asyncio
import time
from collections import deque
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from .capture import MAX_LABEL_LENGTH, Capture, validate_observation_text
from .const import STALE_SECONDS

PRE_SECONDS = 180
POST_SECONDS = 180
RAW_BIT_POST_SECONDS = 600
# Bound extensions relative to the first event, independently of prehistory.
MAX_POST_SECONDS = 900
RAW_BIT_TRIGGERS = {
    "raw_118000_01f8": 11,
    "raw_118000_03b6": 1,
    "raw_118007_0191": 1,
}
RING_BYTES = 524_288
RING_CHUNKS = 8192
MAX_CLOCK_SKEW_SECONDS = 1.0
MAX_CAPTURES = 4
MAX_EVENTS = 32
EVENT_STATUSES = ("disabled", "waiting", "recording", "ready")


class EventCapture:
    """Retain the latest bounded event windows independently of manual captures."""

    def __init__(self, enabled=False, on_change=None):
        self.enabled = enabled
        self.on_change = on_change
        self.capture = Capture(POST_SECONDS, on_change)
        self.ring = deque()
        self.ring_size = 0
        self.baseline = None
        self.status_baseline = None
        self.raw_bit_baselines = {}
        self.first_event_time = None
        self.post_seconds = POST_SECONDS
        self.events = []
        self.omitted_events = 0
        self.pre_seconds = 0.0
        self.previous_captures = []
        self.overwritten_captures = 0

    def _notify(self):
        if self.on_change:
            self.on_change()

    @property
    def status(self):
        if self.capture.reason == "recording":
            return "recording"
        if self.capture.reason != "idle":
            return "ready"
        return "waiting" if self.enabled else "disabled"

    def configure(self, enabled):
        if enabled == self.enabled:
            return
        self.enabled = enabled
        self.disconnect("disabled")
        self._notify()

    def clear(self):
        self.ring.clear()
        self.ring_size = 0
        self.baseline = None
        self.status_baseline = None
        self.raw_bit_baselines.clear()
        self.first_event_time = None
        self.post_seconds = POST_SECONDS
        self.events = []
        self.omitted_events = 0
        self.pre_seconds = 0.0
        self.previous_captures = []
        self.overwritten_captures = 0
        self.capture.clear()

    def disconnect(self, reason="disconnected"):
        self.ring.clear()
        self.ring_size = 0
        self.baseline = None
        self.status_baseline = None
        self.raw_bit_baselines.clear()
        self.capture.stop(reason)

    def feed(self, data):
        if not self.enabled or not data:
            return
        self.capture.feed(data)
        now = time.monotonic()
        part = bytes(data[-RING_BYTES:])
        self.ring.append((now, part, datetime.now(UTC), len(data)))
        self.ring_size += len(part)
        while self.ring and (
            now - self.ring[0][0] > PRE_SECONDS
            or self.ring_size > RING_BYTES
            or len(self.ring) > RING_CHUNKS
        ):
            self.ring_size -= len(self.ring.popleft()[1])

    def export_recent_received(self) -> dict | None:
        """Copy the opt-in receive suffix with original UTC; never start a capture.

        This partial snapshot is separate from event windows and can start in the
        middle of a frame. Clock discontinuities cannot be repaired by projecting
        the export clock backwards onto received bytes.
        """
        if not self.enabled:
            return None
        now, exported = time.monotonic(), datetime.now(UTC)
        recent = [row for row in self.ring if 0 <= now - row[0] <= PRE_SECONDS]
        if not recent or any(len(row) != 4 for row in recent):
            return None
        start, _, first_utc, _ = recent[0]
        previous, previous_utc = start, first_utc
        for stamp, _, received, _ in recent:
            if (
                not isinstance(received, datetime)
                or received.tzinfo is None
                or received.utcoffset() != timedelta(0)
                or not isinstance(first_utc, datetime)
                or first_utc.tzinfo is None
                or stamp < previous
                or received < previous_utc
                or received > exported
                or abs((received - first_utc).total_seconds() - (stamp - start))
                > MAX_CLOCK_SKEW_SECONDS
            ):
                return None
            previous, previous_utc = stamp, received
        last, _, last_utc, _ = recent[-1]
        if (
            abs((exported - last_utc).total_seconds() - (now - last))
            > MAX_CLOCK_SKEW_SECONDS
        ):
            return None
        return {
            "format_version": 1,
            "source_kind": "passive_received_snapshot",
            "status": "partial",
            "completion_reason": "passive_snapshot",
            "timestamp_basis": "original_received_utc_and_monotonic_elapsed",
            "started_utc": first_utc.isoformat(),
            "received_until_utc": last_utc.isoformat(),
            "exported_at_utc": exported.isoformat(),
            "chunks": [
                {
                    "elapsed_ms": round((stamp - start) * 1000),
                    "received_utc": received.isoformat(),
                    "hex": part.hex(),
                }
                for stamp, part, received, _ in recent
            ],
            "bytes": sum(len(part) for _, part, _, _ in recent),
            "chunk_count": len(recent),
            "max_age_seconds": PRE_SECONDS,
            "max_bytes": RING_BYTES,
            "max_chunks": RING_CHUNKS,
            "prefix_bytes_omitted": sum(
                size - len(part) for _, part, _, size in recent
            ),
            "clock_skew_tolerance_seconds": MAX_CLOCK_SKEW_SECONDS,
        }

    def observe_rpm(self, rpm):
        """Called only for checksum-, identity- and range-validated readings."""
        if not self.enabled:
            return
        now = time.monotonic()
        running = rpm > 0
        previous = self.baseline
        self.baseline = (running, now)
        # Initial data, reconnects and stale gaps establish a new baseline.
        if (
            previous is None
            or now - previous[1] >= STALE_SECONDS
            or previous[0] == running
        ):
            return
        self._record_event(
            now, "compressor_started" if running else "compressor_stopped", rpm=rpm
        )

    def observe_status(self, raw):
        """Observe bit 28 of a validated 0208 response, without assigning meaning."""
        if not self.enabled:
            return
        now = time.monotonic()
        word = int.from_bytes(bytes.fromhex(raw), "little")
        active = bool(word & (1 << 28))
        previous = self.status_baseline
        self.status_baseline = (active, now)
        if (
            previous is None
            or now - previous[1] >= STALE_SECONDS
            or previous[0] == active
        ):
            return
        self._record_event(now, "status_0208_bit_28_changed", active=active, raw=raw)

    def trigger_diagnostic(self, label):
        """Explicit local trigger; the label is not a decoded BDE observation."""
        try:
            label = validate_observation_text(label, MAX_LABEL_LENGTH)
        except ValueError as err:
            raise ValueError("invalid_event_label") from err
        if not self.enabled:
            raise ValueError("event_capture_disabled")
        now = time.monotonic()
        if not self.ring or now - self.ring[-1][0] >= STALE_SECONDS:
            raise ValueError("event_capture_no_recent_data")
        self._finish_due_capture(now)
        joined = self.capture.reason == "recording"
        if joined and len(self.events) >= MAX_EVENTS:
            raise ValueError("event_capture_event_limit")
        self._record_event(now, "diagnostic_trigger", label=label)
        return {
            "started_utc": self.capture.started,
            "elapsed_ms": self.events[-1]["elapsed_ms"],
            "label": label,
            "joined_existing_capture": joined,
        }

    def observe_raw_bit(self, key, raw):
        """Record exact decoder-validated bit edges, without a PTC interpretation."""
        if not self.enabled or key not in RAW_BIT_TRIGGERS:
            return
        now = time.monotonic()
        bit = RAW_BIT_TRIGGERS[key]
        active = bool(int.from_bytes(bytes.fromhex(raw), "little") & (1 << bit))
        previous = self.raw_bit_baselines.get(key)
        self.raw_bit_baselines[key] = (active, now)
        if (
            previous is None
            or now - previous[1] >= STALE_SECONDS
            or previous[0] == active
        ):
            return
        self._record_event(
            now,
            "raw_bit_changed",
            post_seconds=RAW_BIT_POST_SECONDS,
            key=key,
            bit=bit,
            active=active,
            raw=raw,
        )

    def _finish_due_capture(self, now):
        # A service can run before an overdue timer, without an incoming chunk.
        if (
            self.capture.reason == "recording"
            and now - self.capture.monotonic_start >= self.capture.recording_duration
        ):
            self.capture.stop("duration_limit")

    def _record_event(self, now, event_type, *, post_seconds=None, **details):
        """Share bounded recording windows across independent trigger sources."""
        self._finish_due_capture(now)
        if (
            post_seconds is not None
            and self.capture.reason == "recording"
            and now + post_seconds > self.first_event_time + MAX_POST_SECONDS
        ):
            # Preserve the old partial window and start another with prehistory.
            # Never silently truncate a requested photo window or grow forever.
            self.capture.stop("candidate_retriggered")
        if self.capture.reason != "recording":
            if self.capture.reason != "idle":
                self.previous_captures.append(self._export_current())
                if len(self.previous_captures) >= MAX_CAPTURES:
                    self.previous_captures.pop(0)
                    self.overwritten_captures += 1
            self.events = []
            self.omitted_events = 0
            self.first_event_time = now
            self.post_seconds = POST_SECONDS
            # on_data already buffered the chunk containing this transition.
            before = [(t, p) for t, p, *_ in self.ring if now - t <= PRE_SECONDS]
            start = before[0][0] if before else now
            self.pre_seconds = now - start
            self.capture.start()
            self.capture.monotonic_start = start
            self.capture.started = (
                datetime.now(UTC) - timedelta(seconds=self.pre_seconds)
            ).isoformat()
            self.capture.recording_duration = self.pre_seconds + POST_SECONDS
            self.capture.chunks = [
                {"elapsed_ms": round((t - start) * 1000), "hex": p.hex()}
                for t, p in before
            ]
            self.capture.size = sum(len(p) for _, p in before)
        if post_seconds is not None:
            self.post_seconds = post_seconds
            self.capture.recording_duration = (
                now - self.capture.monotonic_start + post_seconds
            )
            self.capture.timer.cancel()
            self.capture.timer = asyncio.get_running_loop().call_later(
                post_seconds, self.capture.stop, "duration_limit"
            )
        if len(self.events) < MAX_EVENTS:
            self.events.append(
                {
                    "elapsed_ms": round((now - self.capture.monotonic_start) * 1000),
                    "type": event_type,
                    **details,
                }
            )
        else:
            self.omitted_events += 1
        # Only explicit raw-bit edges extend the bounded photo window.
        self._notify()

    def summary(self):
        return {
            **self.capture.summary(),
            "status": self.status,
            "completion_reason": self.capture.reason,
            "enabled": self.enabled,
            "pre_duration_seconds": round(self.pre_seconds, 3),
            "requested_pre_seconds": PRE_SECONDS,
            "requested_post_seconds": self.post_seconds,
            "max_post_seconds": MAX_POST_SECONDS,
            "event_count": len(self.events),
            "omitted_events": self.omitted_events,
            "capture_count": len(self.previous_captures)
            + int(self.capture.reason != "idle"),
            "max_captures": MAX_CAPTURES,
            "overwritten_captures": self.overwritten_captures,
        }

    def _export_current(self):
        return {
            **self.capture.export(),
            **self.summary(),
            "events": [dict(event) for event in self.events],
        }

    def export(self):
        return {
            **self._export_current(),
            "previous_captures": deepcopy(self.previous_captures),
        }
