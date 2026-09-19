"""One receive-only connection and per-value freshness per entry."""

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant, callback

from .capture import DURATION, Capture
from .const import PROFILE, STALE_SECONDS
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
        integration_version: str | None = None,
        profile: str = PROFILE,
    ) -> None:
        self.diagnostic_listeners: set[Callable[[], None]] = set()
        self.capture = Capture(capture_duration, self._notify_diagnostics)
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
                async with open_receiver(self.host, self.port) as reader:
                    self.connected = True
                    self._notify()
                    self._notify_diagnostics()
                    async for readings in receive(
                        reader, self.decoder, on_data=self._capture_data
                    ):
                        now = time.monotonic()
                        self.last_valid_received = datetime.now(UTC)
                        for reading in readings:
                            self.values[reading.key] = (reading, now)
                        delay = 1
                        self.last_error = None
                        self.ready.set()
                        self._notify()
            except (OSError, TimeoutError, NoSupportedData) as err:
                # Do not expose endpoint or raw traffic through diagnostics/logs.
                self.last_error = type(err).__name__
                _LOGGER.debug("Receiver reconnect: %s", self.last_error)
            finally:
                self.connected = False
                self.values.clear()
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
    def _capture_data(self, data: bytes) -> None:
        self.capture.feed(data)

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
            # Retain the diagnostic field; the receiver has no send path.
            "application_bytes_sent": 0,
        }
