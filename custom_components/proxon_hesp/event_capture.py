"""Opt-in, bounded pre/post recording of validated compressor transitions."""

import time
from collections import deque
from datetime import UTC, datetime, timedelta

from .capture import Capture
from .const import STALE_SECONDS

PRE_SECONDS = 60
POST_SECONDS = 180
RING_BYTES = 262_144
RING_CHUNKS = 1024
MAX_EVENTS = 32
EVENT_STATUSES = ("disabled", "waiting", "recording", "ready")


class EventCapture:
    """Keep one event until explicitly cleared; never replace manual captures."""

    def __init__(self, enabled=False, on_change=None):
        self.enabled = enabled
        self.on_change = on_change
        self.capture = Capture(POST_SECONDS, on_change)
        self.ring = deque()
        self.ring_size = 0
        self.baseline = None
        self.events = []
        self.omitted_events = 0
        self.pre_seconds = 0.0

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
        self.events = []
        self.omitted_events = 0
        self.pre_seconds = 0.0
        self.capture.clear()

    def disconnect(self, reason="disconnected"):
        self.ring.clear()
        self.ring_size = 0
        self.baseline = None
        self.capture.stop(reason)

    def feed(self, data):
        if not self.enabled or not data:
            return
        if self.capture.reason != "idle":
            self.capture.feed(data)
            return
        now = time.monotonic()
        part = bytes(data[-RING_BYTES:])
        self.ring.append((now, part))
        self.ring_size += len(part)
        while self.ring and (
            now - self.ring[0][0] > PRE_SECONDS
            or self.ring_size > RING_BYTES
            or len(self.ring) > RING_CHUNKS
        ):
            self.ring_size -= len(self.ring.popleft()[1])

    def observe_rpm(self, rpm):
        """Called only for checksum-, identity- and range-validated readings."""
        if not self.enabled or self.status == "ready":
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
        if self.capture.reason == "idle":
            # on_data already buffered the chunk containing this transition.
            before = [(t, p) for t, p in self.ring if now - t <= PRE_SECONDS]
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
            self.ring.clear()
            self.ring_size = 0
        if len(self.events) < MAX_EVENTS:
            self.events.append(
                {
                    "elapsed_ms": round((now - self.capture.monotonic_start) * 1000),
                    "type": "compressor_started" if running else "compressor_stopped",
                    "rpm": rpm,
                }
            )
        else:
            self.omitted_events += 1
        # Further transitions do not extend the fixed post-event timer.
        self._notify()

    def summary(self):
        return {
            **self.capture.summary(),
            "status": self.status,
            "completion_reason": self.capture.reason,
            "enabled": self.enabled,
            "pre_duration_seconds": round(self.pre_seconds, 3),
            "requested_pre_seconds": PRE_SECONDS,
            "requested_post_seconds": POST_SECONDS,
            "event_count": len(self.events),
            "omitted_events": self.omitted_events,
        }

    def export(self):
        return {
            **self.capture.export(),
            **self.summary(),
            "events": [dict(event) for event in self.events],
        }
