"""Explicit, bounded in-memory recording of the existing receive stream."""

import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime

MAX_BYTES = 1_048_576
MAX_CHUNKS = 16384
DURATION = 120
MIN_DURATION = 30
MAX_DURATION = 600
STATUSES = (
    "idle",
    "recording",
    "manual",
    "duration_limit",
    "byte_limit",
    "chunk_limit",
    "disconnected",
)


def validate_duration(value: int) -> int:
    """Keep limits enforced outside the options UI as well."""
    if type(value) is not int or not MIN_DURATION <= value <= MAX_DURATION:
        raise ValueError("Capture duration must be an integer from 30 to 600 seconds")
    return value


class Capture:
    def __init__(
        self, duration: int = DURATION, on_change: Callable[[], None] | None = None
    ):
        self.duration = validate_duration(duration)
        self.on_change = on_change
        self.timer = None
        self._reset()

    def _reset(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        self.started = None
        self.stopped = None
        self.monotonic_start = 0.0
        self.actual_duration = 0.0
        self.recording_duration = self.duration
        self.chunks = []
        self.size = 0
        self.reason = "idle"

    def _notify(self):
        if self.on_change is not None:
            self.on_change()

    def clear(self):
        self._reset()
        self._notify()

    def start(self):
        self._reset()
        self.started = datetime.now(UTC).isoformat()
        self.monotonic_start = time.monotonic()
        self.reason = "recording"
        self.timer = asyncio.get_running_loop().call_later(
            self.recording_duration, self.stop, "duration_limit"
        )
        self._notify()

    def stop(self, reason="manual"):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        if self.reason == "recording":
            self.actual_duration = max(0.0, time.monotonic() - self.monotonic_start)
            self.stopped = datetime.now(UTC).isoformat()
            self.reason = reason
            self._notify()

    def feed(self, data):
        if self.reason != "recording" or not data:
            return
        # The event loop may deliver buffered data before an overdue timer.
        if time.monotonic() - self.monotonic_start >= self.recording_duration:
            self.stop("duration_limit")
            return
        remaining = MAX_BYTES - self.size
        part = data[:remaining]
        self.chunks.append(
            {
                "elapsed_ms": round((time.monotonic() - self.monotonic_start) * 1000),
                "hex": part.hex(),
            }
        )
        self.size += len(part)
        if self.size >= MAX_BYTES:
            self.stop("byte_limit")
        elif len(self.chunks) >= MAX_CHUNKS:
            self.stop("chunk_limit")

    def summary(self):
        """Small status snapshot; never copy or expose raw payloads in entities."""
        elapsed = (
            max(0.0, time.monotonic() - self.monotonic_start)
            if self.reason == "recording"
            else self.actual_duration
        )
        return {
            "started_utc": self.started,
            "stopped_utc": self.stopped,
            "status": self.reason,
            "actual_duration_seconds": round(elapsed, 3),
            "bytes": self.size,
            "chunk_count": len(self.chunks),
            "max_bytes": MAX_BYTES,
            "max_chunks": MAX_CHUNKS,
            "duration_seconds": self.recording_duration,
            "configured_duration_seconds": self.duration,
        }

    def export(self):
        return {
            "format_version": 2,
            **self.summary(),
            "chunks": [dict(chunk) for chunk in self.chunks],
        }
