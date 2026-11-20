"""Bounded BDE indications from fresh validated source frames."""

import math

from .hesp.decoder import Reading

SOURCE_KEYS = {
    "operating_mode": "operating_mode",
    "controller_fan_level": "raw_0208",
    "raw_006c": "raw_006c",
    "raw_051c": "compressor_rpm",
}
MAX_SOURCE_AGE = 6.0
STABILITY_SECONDS = 15.0
# Only complete, independently display-backed contexts belong here.
HEATING_CONTEXTS = frozenset(
    {
        ("eco_winter", 0x82001312, 0x27),
        ("eco_winter", 0x8200131A, 0x27),
        ("eco_winter", 0x82009312, 0x27),
    }
)

BLANK_CONTEXT = ("eco_winter", 0x8000100A, 0x25)


UPPER_GREEN_LED_CONTEXTS = {
    ("eco_winter", "0a100080"): False,
    ("eco_winter", "12130082"): True,
    ("comfort", "1a130080"): True,
}
LED_SOURCE_KEYS = ("operating_mode", "raw_0208")


class BdeDisplay:
    """Report observed BDE indications from validated sources.

    Only the decoder's validated-frame observer advances this tracker. Entity
    property reads cannot turn an unchanged cached snapshot into an indication.
    """

    def __init__(self, *, supports_green_led: bool = False) -> None:
        self._supports_green_led = supports_green_led
        self._sources: dict[str, tuple[Reading, float]] = {}
        self._green_led: tuple[bool, float, float] | None = None
        self._led_status_current = False
        self._context: tuple[str, int, int] | None = None
        self._since: float | None = None
        self._qualified = False

    def reset(self) -> None:
        """Forget both observations and stability across connection lifecycles."""
        self._sources.clear()
        self._reset_stability()
        self._green_led = None
        self._led_status_current = False

    def _reset_stability(self) -> None:
        self._context = None
        self._since = None
        self._qualified = False

    def observe(self, source: str, readings: list[Reading], now: float) -> bool:
        """Accept one exact checksum-validated source frame in wire order."""
        key = SOURCE_KEYS.get(source)
        if key is None:
            return False
        was_qualified = self._qualified
        previous_led = self._green_led[0] if self._green_led is not None else None
        # Check the old snapshot before replacing anything: a new valid batch
        # must never bridge a period during which any source had expired.
        if self._valid_context(now) is None:
            self._reset_stability()
        reading = next((item for item in readings if item.key == key), None)
        previous = self._sources.get(key)
        if reading is None:
            # A valid frame with a rejected mode/RPM invalidates the old value.
            self._sources.pop(key, None)
            self._reset_stability()
        elif previous is not None and now < previous[1]:
            # Non-monotonic receipts cannot extend the proof window.
            self._reset_stability()
            reading = None
        else:
            self._sources[key] = (reading, now)
            context = self._valid_context(now)
            if context is None:
                self._reset_stability()
            elif context != self._context:
                self._reset_stability()
                self._context = context
                self._since = now
            elif self._since is not None and now - self._since >= STABILITY_SECONDS:
                self._qualified = True
        if self._supports_green_led and key in LED_SOURCE_KEYS:
            self._update_green_led(key, previous, reading, now)
        return self._qualified != was_qualified or self.green_led(now) != previous_led

    def _valid_context(self, now: float) -> tuple[str, int, int] | None:
        if len(self._sources) != len(SOURCE_KEYS):
            return None
        stamps = [stamp for _, stamp in self._sources.values()]
        if any(not 0 <= now - stamp <= MAX_SOURCE_AGE for stamp in stamps):
            return None
        if max(stamps) - min(stamps) > MAX_SOURCE_AGE:
            return None
        mode = self._sources["operating_mode"][0].value
        status = self._sources["raw_0208"][0].value
        valves = self._sources["raw_006c"][0].value
        rpm = self._sources["compressor_rpm"][0].value
        if not isinstance(mode, str) or type(rpm) not in (int, float):
            return None
        if not 0 <= rpm <= 10000 or not math.isfinite(rpm):
            return None
        if not isinstance(status, str) or not isinstance(valves, str):
            return None
        if len(status) != 8 or len(valves) != 8:
            return None
        try:
            context = (
                mode,
                int.from_bytes(bytes.fromhex(status), "little"),
                int.from_bytes(bytes.fromhex(valves), "little"),
            )
        except ValueError:
            return None
        if context in HEATING_CONTEXTS and rpm > 0:
            return context
        return context if context == BLANK_CONTEXT and rpm == 0 else None

    @property
    def expires_at(self) -> float | None:
        """Earliest source deadline for an already qualified indication."""
        if not self._qualified:
            return None
        return min(stamp for _, stamp in self._sources.values()) + MAX_SOURCE_AGE

    def value(self, now: float) -> str | None:
        """Recheck availability between expiry callbacks without advancing state."""
        if self._qualified and self._valid_context(now) == self._context:
            return "blank" if self._context == BLANK_CONTEXT else "heating"
        return None

    def _update_green_led(
        self,
        key: str,
        previous: tuple[Reading, float] | None,
        reading: Reading | None,
        now: float,
    ) -> None:
        # A mode change must be followed by a new status receipt. In
        # particular, switching back cannot revive the old mode's LED state.
        if key == "raw_0208":
            self._led_status_current = reading is not None
        elif reading is None or (
            previous is not None and previous[0].value != reading.value
        ):
            self._led_status_current = False
        self._green_led = None
        if not self._led_status_current:
            return
        mode = self._sources.get("operating_mode")
        status = self._sources.get("raw_0208")
        if mode is None or status is None:
            return
        state = UPPER_GREEN_LED_CONTEXTS.get((mode[0].value, status[0].value))
        latest = max(mode[1], status[1])
        deadline = min(mode[1], status[1]) + MAX_SOURCE_AGE
        if state is not None and latest <= now <= deadline:
            self._green_led = state, latest, deadline

    @property
    def green_led_expires_at(self) -> float | None:
        return self._green_led[2] if self._green_led is not None else None

    def green_led(self, now: float) -> bool | None:
        """Mirror the upper green LED while both matching sources are fresh."""
        if self._green_led is not None:
            state, latest, deadline = self._green_led
            if latest <= now <= deadline:
                return state
        return None

    def expire(self, now: float) -> bool:
        """Clear an expired candidate and report whether listeners need updating."""
        display_expired = self._since is not None and self._valid_context(now) is None
        if display_expired:
            self._reset_stability()
        led_expired = self._green_led is not None and self.green_led(now) is None
        if led_expired:
            self._green_led = None
        return display_expired or led_expired
