"""Explicit one-shot experiment; never a persistent temperature controller."""

import asyncio
import math
import secrets
import struct
import time
from typing import TYPE_CHECKING

from .capture import Capture
from .hesp.checksum import checksum

if TYPE_CHECKING:
    from .coordinator import ProxonRuntime

BASELINE_SECONDS = 10
TOKEN_SECONDS = 60
FRESH_SECONDS = 10


class ExperimentRejected(Exception):
    """A test precondition failed before attempting a write."""


def _target_frame(temperature: float) -> bytes:
    """Only the observed panel SET for DP 0x0227, Float32 LE, local limits."""
    if not math.isfinite(temperature) or not 18 <= temperature <= 30:
        raise ExperimentRejected("Test temperature must be within 18–30 °C.")
    body = bytes.fromhex("1180002702000008") + struct.pack("<f", temperature)
    crc = checksum(body)
    assert crc is not None
    return body + crc.to_bytes(2, "little")


class TargetTemperatureTest:
    """One attempt per loaded runtime, over its existing TCP connection only."""

    def __init__(self, runtime: ProxonRuntime) -> None:
        self.runtime = runtime
        self.capture = Capture()
        self.writer: asyncio.StreamWriter | None = None
        self.token: str | None = None
        self.prepared_at = 0.0
        self.original: float | None = None
        self.requested: float | None = None
        self.attempts = 0
        self.bytes_offered = 0
        self.outcome = "idle"
        self.tx: dict | None = None

    def connection_changed(self, writer: asyncio.StreamWriter | None) -> None:
        if writer is not self.writer:
            self._invalidate("connection_changed")
            self.capture.stop("disconnected")
        self.writer = writer

    def _invalidate(self, reason: str) -> None:
        if self.token is not None:
            self.token = None
            self.outcome = reason

    def _current_temperature(self) -> float:
        if (
            not self.runtime.connected
            or self.writer is None
            or self.writer.is_closing()
        ):
            raise ExperimentRejected("No existing connected gateway stream.")
        now = time.monotonic()
        for key in ("target_temperature", "operating_mode"):
            item = self.runtime.values.get(key)
            if item is None or not 0 <= now - item[1] < FRESH_SECONDS:
                raise ExperimentRejected(
                    "Fresh target temperature and operating mode needed."
                )
        if self.runtime.values["operating_mode"][0].value != "comfort":
            raise ExperimentRejected("This experiment is restricted to Comfort mode.")
        return float(self.runtime.values["target_temperature"][0].value)

    def observe(self) -> None:
        """Invalidate even if an intervening panel change is later reverted."""
        if self.token is None:
            return
        try:
            if self._current_temperature() != self.original:
                self._invalidate("panel_changed")
        except ExperimentRejected:
            self._invalidate("state_unavailable_or_changed")

    def prepare(self, expected_temperature: float, delta: float) -> dict:
        if self.attempts:
            raise ExperimentRejected(
                "Attempt already consumed. Save diagnostics before reload."
            )
        now = time.monotonic()
        if self.token is not None and now - self.prepared_at < TOKEN_SECONDS:
            raise ExperimentRejected("A test is already prepared.")
        original = self._current_temperature()
        if (
            not math.isfinite(expected_temperature)
            or not 18 <= original <= 30
            or expected_temperature != original
        ):
            raise ExperimentRejected(
                "The confirmed BDE setpoint differs from the received value."
            )
        if delta not in (-0.5, 0.5):
            raise ExperimentRejected("Only a change of -0.5 or +0.5 °C is allowed.")
        requested = original + delta
        _target_frame(requested)
        self.original = original
        self.requested = requested
        self.prepared_at = now
        self.token = secrets.token_urlsafe(24)
        self.outcome = "prepared"
        self.capture.start()
        return {
            "confirmation_token": self.token,
            "original_temperature": original,
            "test_temperature": requested,
            "minimum_wait_seconds": BASELINE_SECONDS,
            "expires_in_seconds": TOKEN_SECONDS,
        }

    async def send(self, token: str) -> dict:
        if (
            self.token is None
            or not token.isascii()
            or not secrets.compare_digest(token, self.token)
        ):
            raise ExperimentRejected("No matching armed test. Nothing sent.")
        age = time.monotonic() - self.prepared_at
        if age >= TOKEN_SECONDS:
            self._invalidate("expired")
            raise ExperimentRejected("Confirmation expired. Nothing sent.")
        if age < BASELINE_SECONDS:
            raise ExperimentRejected(
                "Wait at least 10 seconds for the baseline recording."
            )
        self.observe()
        if self.token is None:
            raise ExperimentRejected(
                "Panel state changed or is unavailable. Nothing sent."
            )
        if self.capture.reason != "recording":
            self._invalidate("capture_stopped")
            raise ExperimentRejected("Test recording stopped. Nothing sent.")
        assert self.writer is not None and self.requested is not None
        writer = self.writer
        frame = _target_frame(self.requested)
        # Consume BEFORE write and before the first await: concurrent calls,
        # cancellation and ambiguous network errors must never cause a retry.
        self.token = None
        self.attempts = 1
        self.bytes_offered = len(frame)
        self.outcome = "delivery_unknown"
        self.tx = {
            "elapsed_ms": round(
                (time.monotonic() - self.capture.monotonic_start) * 1000
            ),
            "direction": "tx_attempt",
            "hex": frame.hex(),
        }
        writer.write(frame)
        async with asyncio.timeout(2):
            await writer.drain()
        self.outcome = "transport_flushed_unverified"
        return {
            "outcome": self.outcome,
            "original_temperature": self.original,
            "test_temperature": self.requested,
            "write_attempts": self.attempts,
        }

    def diagnostics(self) -> dict:
        # Never include the confirmation token or endpoint.
        outcome = self.outcome
        if (
            self.token is not None
            and time.monotonic() - self.prepared_at >= TOKEN_SECONDS
        ):
            outcome = "expired"
        return {
            "outcome": outcome,
            "original_temperature": self.original,
            "test_temperature": self.requested,
            "write_attempts": self.attempts,
            "application_bytes_offered": self.bytes_offered,
            "transmission_attempt": dict(self.tx) if self.tx else None,
            "receive_capture": self.capture.export(),
        }

    def close(self) -> None:
        self.connection_changed(None)
        self.stop_capture(clear=True)

    def stop_capture(self, *, clear: bool = False) -> None:
        """Stop/erase via the existing buttons without re-enabling another write."""
        self._invalidate("capture_stopped")
        if clear:
            self.capture.clear()
            self.original = self.requested = None
            self.tx = None
            self.outcome = "cleared"
        else:
            self.capture.stop()
