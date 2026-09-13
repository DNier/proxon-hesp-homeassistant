"""Explicit, bounded in-memory recording of the existing receive stream."""

import asyncio
import time
from datetime import UTC, datetime

MAX_BYTES = 1_048_576
MAX_CHUNKS = 4096
DURATION = 120


class Capture:
    def __init__(self):
        self.timer = None
        self.clear()

    def clear(self):
        self.stop("cleared")
        self.started = None
        self.monotonic_start = 0.0
        self.chunks = []
        self.size = 0
        self.reason = "idle"

    def start(self):
        self.clear()
        self.started = datetime.now(UTC).isoformat()
        self.monotonic_start = time.monotonic()
        self.reason = "recording"
        self.timer = asyncio.get_running_loop().call_later(
            DURATION, self.stop, "duration_limit"
        )

    def stop(self, reason="manual"):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        if getattr(self, "reason", None) == "recording":
            self.reason = reason

    def feed(self, data):
        if self.reason != "recording":
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
        if self.size >= MAX_BYTES or len(self.chunks) >= MAX_CHUNKS:
            self.stop("size_limit")

    def export(self):
        return {
            "format_version": 1,
            "started_utc": self.started,
            "status": self.reason,
            "bytes": self.size,
            "max_bytes": MAX_BYTES,
            "max_chunks": MAX_CHUNKS,
            "duration_seconds": DURATION,
            "chunks": [dict(chunk) for chunk in self.chunks],
        }
