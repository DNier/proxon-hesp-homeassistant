"""One connection, per-value freshness and explicit calendar correction."""

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .capture import DURATION, Capture
from .const import PROFILE, STALE_SECONDS
from .event_capture import EventCapture
from .hesp.calendar import calendar_frame, calendar_payload
from .hesp.decoder import Decoder, Reading, Statistics
from .hesp.transport import NoSupportedData, open_receiver, receive

_LOGGER = logging.getLogger(__name__)


class ProxonRuntime:
    """Own network lifecycle; all UI properties read cached values only."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        *,
        capture_duration: int = DURATION,
        event_capture_enabled: bool = False,
        integration_version: str | None = None,
        profile: str = PROFILE,
    ) -> None:
        self.room_updates = []
        self.room_config = []
        self.diagnostic_listeners: set[Callable[[], None]] = set()
        self.capture = Capture(capture_duration, self._notify_diagnostics)
        self.event_capture = EventCapture(
            event_capture_enabled, self._notify_diagnostics
        )
        self.integration_version = integration_version
        self.profile = profile
        self.last_valid_received: datetime | None = None
        self.hass = hass
        self.host = host
        self.port = port
        self.connected = False
        self.values: dict[str, tuple[Reading, float]] = {}
        self.listeners: set[Callable[[], None]] = set()
        self.ready = asyncio.Event()
        self.last_error: str | None = None
        self.reconnects = 0
        self.decoder = Decoder()
        self.previous_stats = Statistics()
        self.task: asyncio.Task | None = None
        self.timer: asyncio.TimerHandle | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.application_bytes_sent = 0
        self.clock_sync_status = "idle"
        self.clock_sync_target: str | None = None
        self._clock_pending: asyncio.Future | None = None
        self._clock_expected: set[int] = set()
        self._clock_last_attempt: float | None = None

    async def start(self, entry) -> None:
        self.task = entry.async_create_background_task(
            self.hass, self._run(), "proxon_hesp_receiver"
        )
        self._schedule_expiry()
        try:
            async with asyncio.timeout(25):
                await self.ready.wait()
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        self.event_capture.clear()
        self.capture.clear()
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        self.connected = False
        self.values.clear()
        self.listeners.clear()
        self.diagnostic_listeners.clear()

    async def _run(self) -> None:
        delay = 1
        while True:
            try:
                async with open_receiver(
                    self.host, self.port, self._set_writer
                ) as reader:
                    self.connected = True
                    self._notify()
                    self._notify_diagnostics()
                    async for readings in receive(
                        reader, self.decoder, on_data=self._capture_data
                    ):
                        now = time.monotonic()
                        self.last_valid_received = datetime.now(UTC)
                        for reading in readings:
                            if reading.key == "compressor_rpm":
                                self.event_capture.observe_rpm(reading.value)
                            self.values[reading.key] = (reading, now)
                            if (
                                reading.key == "uptime"
                                and self._clock_pending is not None
                                and not self._clock_pending.done()
                                and reading.value in self._clock_expected
                            ):
                                self._clock_pending.set_result(True)
                        delay = 1
                        self.last_error = None
                        self.ready.set()
                        self._notify()
            except (OSError, TimeoutError, NoSupportedData) as err:
                # Do not expose endpoint or raw traffic through diagnostics/logs.
                self.last_error = type(err).__name__
                _LOGGER.debug("Receiver reconnect: %s", self.last_error)
            finally:
                self._set_writer(None)
                self.connected = False
                self.values.clear()
                self.event_capture.disconnect()
                self.capture.stop("disconnected")
                self._notify()
                self._notify_diagnostics()
            for name, value in asdict(self.decoder.stats).items():
                setattr(
                    self.previous_stats,
                    name,
                    getattr(self.previous_stats, name) + value,
                )
            self.decoder = Decoder()
            self.reconnects += 1
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    @callback
    def _set_writer(self, writer) -> None:
        self.writer = writer
        if writer is None and self._clock_pending is not None:
            if not self._clock_pending.done():
                self._clock_pending.set_result(False)

    async def sync_clock(self) -> None:
        """One explicit write on the existing connection, never retry on failure."""
        if self._clock_pending is not None:
            raise HomeAssistantError("A device time update is already in progress")
        writer = self.writer
        current = self.get("uptime")
        if writer is None or writer.is_closing() or current is None:
            raise HomeAssistantError("Fresh device calendar data is required")
        now = time.monotonic()
        if self._clock_last_attempt is not None and now - self._clock_last_attempt < 30:
            raise HomeAssistantError(
                "Please wait 30 seconds before another time update"
            )
        local = datetime.now(ZoneInfo(self.hass.config.time_zone))
        try:
            frame = calendar_frame(local)
        except ValueError as err:
            raise HomeAssistantError("Home Assistant date cannot be encoded") from err
        self.clock_sync_target = local.isoformat(timespec="minutes")
        expected = int.from_bytes(calendar_payload(local), "little")
        if current.value == expected:
            self.clock_sync_status = "already_current"
            self._notify_diagnostics()
            return
        self._clock_last_attempt = now
        self._clock_expected = {expected}
        following = local + timedelta(minutes=1)
        if following.year <= 2127:
            self._clock_expected.add(
                int.from_bytes(calendar_payload(following), "little")
            )
        pending = self._clock_pending = asyncio.get_running_loop().create_future()
        self.clock_sync_status = "waiting"
        self._notify_diagnostics()
        try:
            # No await between checking the connection and the single write.
            writer.write(frame)
            self.application_bytes_sent += len(frame)
            async with asyncio.timeout(20):
                await writer.drain()
                confirmed = await pending
            if not confirmed:
                raise HomeAssistantError(
                    "Connection lost; device time update unconfirmed"
                )
            self.clock_sync_status = "confirmed"
        except asyncio.CancelledError:
            self.clock_sync_status = "unconfirmed"
            raise
        except (OSError, TimeoutError, HomeAssistantError) as err:
            self.clock_sync_status = "unconfirmed"
            raise HomeAssistantError(
                "Device time update unconfirmed; check the BDE before retrying"
            ) from err
        finally:
            if not pending.done():
                pending.cancel()
            self._clock_pending = None
            self._clock_expected.clear()
            self._notify_diagnostics()

    @callback
    def _capture_data(self, data: bytes) -> None:
        self.capture.feed(data)
        self.event_capture.feed(data)

    @callback
    def listen(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.listeners.add(listener)
        return lambda: self.listeners.discard(listener)

    @callback
    def _notify(self) -> None:
        for listener in tuple(self.listeners):
            listener()

    @callback
    def listen_diagnostics(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.diagnostic_listeners.add(listener)
        return lambda: self.diagnostic_listeners.discard(listener)

    @callback
    def _notify_diagnostics(self) -> None:
        for listener in tuple(self.diagnostic_listeners):
            listener()

    def _schedule_expiry(self) -> None:
        self.timer = asyncio.get_running_loop().call_later(5, self._expire)

    @callback
    def _expire(self) -> None:
        expired = [key for key in self.values if self.get(key) is None]
        for key in expired:
            del self.values[key]
        if expired:
            self._notify()
        self._notify_diagnostics()
        self._schedule_expiry()

    def get(self, key: str) -> Reading | None:
        item = self.values.get(key)
        if not self.connected or item is None:
            return None
        return item[0] if time.monotonic() - item[1] < STALE_SECONDS else None

    def diagnostics(self) -> dict:
        counters = {
            name: value + getattr(self.previous_stats, name)
            for name, value in asdict(self.decoder.stats).items()
        }
        return {
            "integration_version": self.integration_version,
            "profile": self.profile,
            "capture": {
                **self.capture.export(),
                "integration_version": self.integration_version,
                "profile": self.profile,
            },
            "event_capture": {
                **self.event_capture.export(),
                "integration_version": self.integration_version,
                "profile": self.profile,
            },
            "last_valid_received_utc": (
                self.last_valid_received.isoformat()
                if self.last_valid_received
                else None
            ),
            "connected": self.connected,
            "last_error": self.last_error,
            "reconnects": self.reconnects,
            "statistics": counters,
            "fresh_keys": sorted(key for key in self.values if self.get(key)),
            "application_bytes_sent": self.application_bytes_sent,
            "clock_sync_status": self.clock_sync_status,
            "clock_sync_target": self.clock_sync_target,
        }
