"""Explicit, bounded in-memory recording of the existing receive stream."""

import asyncio
import time
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime

MAX_BYTES = 1_048_576
MAX_CHUNKS = 16384
DURATION = 120
MIN_DURATION = 30
MAX_DURATION = 600
MAX_OBSERVATIONS = 128
MAX_LABEL_LENGTH = 64
MAX_OBSERVATION_LENGTH = 160
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


def validate_observation_text(value: str, limit: int) -> str:
    """Bound user annotations; they are references, never decoded device values."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value)
    ):
        raise ValueError("invalid_observation")
    return value.strip()


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
        self.observations = []
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

    def mark_observation(self, label: str, observation: str) -> dict:
        """Mark a user-observed state on a running manual recording's clock."""
        label = validate_observation_text(label, MAX_LABEL_LENGTH)
        observation = validate_observation_text(observation, MAX_OBSERVATION_LENGTH)
        now = time.monotonic()
        if (
            self.reason == "recording"
            and now - self.monotonic_start >= self.recording_duration
        ):
            self.stop("duration_limit")
        if self.reason != "recording":
            raise ValueError("capture_not_recording")
        if len(self.observations) >= MAX_OBSERVATIONS:
            raise ValueError("observation_limit")
        marker = {
            "elapsed_ms": round(max(0.0, now - self.monotonic_start) * 1000),
            "label": label,
            "observation": observation,
        }
        self.observations.append(marker)
        self._notify()
        return dict(marker)

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
            "observation_count": len(self.observations),
            "max_observations": MAX_OBSERVATIONS,
        }

    def export(self):
        return {
            "format_version": 3,
            **self.summary(),
            "chunks": [dict(chunk) for chunk in self.chunks],
            "observations": [dict(marker) for marker in self.observations],
        }
