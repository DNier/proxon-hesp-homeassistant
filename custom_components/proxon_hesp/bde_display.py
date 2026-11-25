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
# LED-only tolerance for observed unchanged source intervals up to 7.479 s.
MAX_LED_SOURCE_AGE = 8.0
# Bounded tolerance for observed Eco Winter poll intervals above six seconds.
MAX_WINTER_SOURCE_AGE = 7.0
STABILITY_SECONDS = 15.0
# Only complete, independently display-backed contexts belong here.
HEATING_CONTEXTS = frozenset(
    {
        ("eco_winter", 0x82001312, 0x27),
        ("eco_winter", 0x8200131A, 0x27),
        ("eco_winter", 0x82009312, 0x27),
    }
)
# Additional complete references are limited to the selected P2 display.
P2_HEATING_CONTEXTS = frozenset(
    {
        ("eco_winter", 0x8200931A, 0x27),
        ("eco_winter", 0x92009312, 0xA7),
    }
)

BLANK_CONTEXT = ("eco_winter", 0x8000100A, 0x25)
COOLING_CONTEXT = ("comfort", 0x80001522, 0x0227)


UPPER_GREEN_LED_CONTEXTS = {
    ("eco_winter", "0a100080"): False,
    ("eco_winter", "12130082"): True,
    ("eco_winter", "1a130082"): True,
    ("comfort", "1a130080"): True,
}
# These additional optical references include valves and positive compressor
# speed. Keep their complete contexts instead of generalizing a status bit.
CONTEXT_GREEN_LED_CONTEXTS = frozenset(
    {
        ("eco_winter", "12930082", "27000000"),
        ("eco_winter", "12110082", "27000000"),
        ("eco_winter", "1a930082", "27000000"),
        ("eco_winter", "12930092", "a7000000"),
    }
)
# Explicit continuity assumption, not an independently observed LED mapping.
INFERRED_GREEN_LED_CONTEXTS = frozenset(
    {("eco_winter", "1a130092"), ("eco_winter", "12130092")}
)
MODE_STATUS_SOURCE_KEYS = ("operating_mode", "raw_0208")
# Exact P2 references requiring a fresh preceding Eco Winter mode receipt.
P2_CONTROLLER_FAN_LEVELS = {"1a130092": 3, "1a930082": 3}
# This reference also depends on the complete valve word and positive RPM.
P2_CONTEXT_CONTROLLER_FAN_LEVELS = {("eco_winter", "12930092", "a7000000"): 2}
P2_CONTEXT_FAN_WORDS = frozenset(
    status for _, status, _ in P2_CONTEXT_CONTROLLER_FAN_LEVELS
)


class BdeDisplay:
    """Report observed BDE indications from validated sources.

    Only the decoder's validated-frame observer advances this tracker. Entity
    property reads cannot turn an unchanged cached snapshot into an indication.
    """

    def __init__(
        self,
        *,
        supports_green_led: bool = False,
        p2_reference: bool = False,
    ) -> None:
        self._p2_reference = p2_reference
        self._cooling_sources: set[str] = set()
        self._supports_green_led = supports_green_led
        self._sources: dict[str, tuple[Reading, float]] = {}
        self._green_led: tuple[bool, float, float] | None = None
        self._green_led_basis: str | None = None
        self._led_on_continuity = False
        self._led_status_current = False
        self._fan_level_status_confirmed = False
        self._context: tuple[str, int, int] | None = None
        self._since: float | None = None
        self._qualified = False

    def configure_p2_reference(self, enabled: bool) -> bool:
        """Start a fresh observation when the selected BDE variant changes."""
        if enabled == self._p2_reference:
            return False
        self._p2_reference = enabled
        self.reset()
        return True

    def reset(self) -> None:
        """Forget both observations and stability across connection lifecycles."""
        self._sources.clear()
        self._cooling_sources.clear()
        self._reset_stability()
        self._green_led = None
        self._green_led_basis = None
        self._led_on_continuity = False
        self._led_status_current = False
        self._fan_level_status_confirmed = False

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
        previous_led_basis = self._green_led_basis
        previous_fan_level = self.fan_level(now)
        fan_deadline = self.fan_level_expires_at
        if fan_deadline is not None and now > fan_deadline:
            self._fan_level_status_confirmed = False
        if self.green_led(now) is None:
            self._led_on_continuity = False
        # Check the old snapshot before replacing anything: a new valid batch
        # must never bridge a period during which any source had expired.
        if self._valid_context(now) is None:
            self._reset_stability()
        reading = next((item for item in readings if item.key == key), None)
        previous = self._sources.get(key)
        if key == "operating_mode" and (
            reading is None or previous is None or previous[0].value != reading.value
        ):
            self._cooling_sources.clear()
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
            if self._p2_reference and key != "operating_mode":
                self._cooling_sources.add(key)
            context = self._valid_context(now)
            if context is None:
                self._reset_stability()
            elif context != self._context:
                same_qualified_heating = (
                    self._qualified
                    and self._is_heating_context(self._context)
                    and self._is_heating_context(context)
                )
                if not same_qualified_heating:
                    self._reset_stability()
                    self._since = now
                self._context = context
            elif self._since is not None and now - self._since >= STABILITY_SECONDS:
                self._qualified = True
        if self._p2_reference and key in MODE_STATUS_SOURCE_KEYS:
            self._update_fan_level_context(key, previous, reading, now)
        if (
            self._p2_reference
            and self._supports_green_led
            and key in (*MODE_STATUS_SOURCE_KEYS, "compressor_rpm", "raw_006c")
        ):
            self._update_green_led(key, previous, reading, now)
        return (
            self._qualified != was_qualified
            or self.green_led(now) != previous_led
            or self._green_led_basis != previous_led_basis
            or self.fan_level(now) != previous_fan_level
        )

    def _update_fan_level_context(
        self,
        key: str,
        previous: tuple[Reading, float] | None,
        reading: Reading | None,
        now: float,
    ) -> None:
        if key == "raw_0208":
            mode = self._sources.get("operating_mode")
            self._fan_level_status_confirmed = (
                reading is not None
                and (
                    reading.value in P2_CONTROLLER_FAN_LEVELS
                    or reading.value in P2_CONTEXT_FAN_WORDS
                )
                and mode is not None
                and mode[0].value == "eco_winter"
                and 0 <= now - mode[1] <= self._fan_level_source_max_age()
            )
        elif key == "operating_mode" and (
            reading is None
            or reading.value != "eco_winter"
            or previous is None
            or not 0 <= now - previous[1] <= self._fan_level_source_max_age()
        ):
            self._fan_level_status_confirmed = False

    def _fan_level_source_max_age(self) -> float:
        status = self._sources.get("raw_0208")
        return (
            MAX_WINTER_SOURCE_AGE
            if status is not None and status[0].value in P2_CONTEXT_FAN_WORDS
            else MAX_SOURCE_AGE
        )

    def _is_heating_context(self, context: tuple[str, int, int] | None) -> bool:
        return context in HEATING_CONTEXTS or (
            self._p2_reference and context in P2_HEATING_CONTEXTS
        )

    def _source_max_age(self) -> float:
        mode = self._sources.get("operating_mode")
        return (
            MAX_WINTER_SOURCE_AGE
            if mode is not None and mode[0].value == "eco_winter"
            else MAX_SOURCE_AGE
        )

    def _valid_context(self, now: float) -> tuple[str, int, int] | None:
        if len(self._sources) != len(SOURCE_KEYS):
            return None
        stamps = [stamp for _, stamp in self._sources.values()]
        max_age = self._source_max_age()
        if any(not 0 <= now - stamp <= max_age for stamp in stamps):
            return None
        if max(stamps) - min(stamps) > max_age:
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
        if self._is_heating_context(context) and rpm > 0:
            return context
        if (
            self._p2_reference
            and context == COOLING_CONTEXT
            and len(self._cooling_sources) == len(SOURCE_KEYS) - 1
            and rpm > 0
        ):
            return context
        return context if context == BLANK_CONTEXT and rpm == 0 else None

    @property
    def expires_at(self) -> float | None:
        """Earliest source deadline for an already qualified indication."""
        if not self._qualified:
            return None
        return (
            min(stamp for _, stamp in self._sources.values()) + self._source_max_age()
        )

    def value(self, now: float) -> str | None:
        """Recheck availability between expiry callbacks without advancing state."""
        if self._qualified and self._valid_context(now) == self._context:
            if self._context == BLANK_CONTEXT:
                return "blank"
            if self._context == COOLING_CONTEXT:
                return "cooling"
            return "heating"
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
        elif key == "operating_mode" and (
            reading is None
            or (previous is not None and previous[0].value != reading.value)
        ):
            self._led_status_current = False
            self._led_on_continuity = False
        self._green_led = None
        self._green_led_basis = None
        if not self._led_status_current:
            self._led_on_continuity = False
            return
        mode = self._sources.get("operating_mode")
        status = self._sources.get("raw_0208")
        if mode is None or status is None:
            self._led_on_continuity = False
            return
        context = mode[0].value, status[0].value
        state = UPPER_GREEN_LED_CONTEXTS.get(context)
        rpm = self._sources.get("compressor_rpm")
        positive_rpm = (
            rpm is not None
            and isinstance(rpm[0].value, (int, float))
            and not isinstance(rpm[0].value, bool)
            and math.isfinite(rpm[0].value)
            and 0 < rpm[0].value <= 10000
            and 0 <= now - rpm[1] <= MAX_LED_SOURCE_AGE
        )
        latest = max(mode[1], status[1])
        deadline = min(mode[1], status[1]) + MAX_LED_SOURCE_AGE
        basis = "display_reference"
        valves = self._sources.get("raw_006c")
        if (
            state is None
            and positive_rpm
            and valves is not None
            and 0 <= now - valves[1] <= MAX_LED_SOURCE_AGE
            and (*context, valves[0].value) in CONTEXT_GREEN_LED_CONTEXTS
        ):
            state = True
            latest = max(latest, rpm[1], valves[1])
            deadline = min(
                deadline,
                rpm[1] + MAX_LED_SOURCE_AGE,
                valves[1] + MAX_LED_SOURCE_AGE,
            )
        if state is None and context in INFERRED_GREEN_LED_CONTEXTS:
            if self._led_on_continuity and positive_rpm:
                latest = max(latest, rpm[1])
                deadline = min(deadline, rpm[1] + MAX_LED_SOURCE_AGE)
                state = True
                basis = "inferred_continuity"
        if state is not None and latest <= now <= deadline:
            self._green_led = state, latest, deadline
            self._green_led_basis = basis
            self._led_on_continuity = (
                state and mode[0].value == "eco_winter" and positive_rpm
            )
        else:
            self._led_on_continuity = False

    @property
    def green_led_expires_at(self) -> float | None:
        return self._green_led[2] if self._green_led is not None else None

    def green_led(self, now: float) -> bool | None:
        """Report a display-backed or explicitly inferred LED while fresh."""
        if self._green_led is not None:
            state, latest, deadline = self._green_led
            if latest <= now <= deadline:
                return state
        return None

    def green_led_basis(self, now: float) -> str | None:
        """Keep continuity assumptions distinguishable from display references."""
        return self._green_led_basis if self.green_led(now) is not None else None

    @property
    def fan_level_expires_at(self) -> float | None:
        if not self._fan_level_status_confirmed:
            return None
        status = self._sources.get("raw_0208")
        if status is not None and status[0].value in P2_CONTEXT_FAN_WORDS:
            if len(self._sources) != len(SOURCE_KEYS):
                return None
            context = tuple(
                self._sources[key][0].value
                for key in ("operating_mode", "raw_0208", "raw_006c")
            )
            rpm = self._sources["compressor_rpm"][0].value
            if (
                context not in P2_CONTEXT_CONTROLLER_FAN_LEVELS
                or type(rpm) not in (int, float)
                or not math.isfinite(rpm)
                or not 0 < rpm <= 10000
            ):
                return None
            return (
                min(stamp for _, stamp in self._sources.values())
                + MAX_WINTER_SOURCE_AGE
            )
        return (
            min(self._sources[key][1] for key in MODE_STATUS_SOURCE_KEYS)
            + MAX_SOURCE_AGE
        )

    def fan_level_confirmed(self, now: float) -> bool:
        """Require a status received in a continuous, fresh Eco Winter context."""
        deadline = self.fan_level_expires_at
        return (
            deadline is not None
            and max(
                self._sources[key][1]
                for key in (
                    tuple(SOURCE_KEYS.values())
                    if self._sources["raw_0208"][0].value in P2_CONTEXT_FAN_WORDS
                    else MODE_STATUS_SOURCE_KEYS
                )
            )
            <= now
            <= deadline
        )

    def fan_level(self, now: float) -> int | None:
        """Return only the P2 word or complete context whose sources are fresh."""
        if not self.fan_level_confirmed(now):
            return None
        status = self._sources["raw_0208"][0].value
        if status in P2_CONTEXT_FAN_WORDS:
            context = tuple(
                self._sources[key][0].value
                for key in ("operating_mode", "raw_0208", "raw_006c")
            )
            return P2_CONTEXT_CONTROLLER_FAN_LEVELS.get(context)
        return P2_CONTROLLER_FAN_LEVELS.get(status)

    def expire(self, now: float) -> bool:
        """Clear an expired candidate and report whether listeners need updating."""
        display_expired = self._since is not None and self._valid_context(now) is None
        if display_expired:
            self._reset_stability()
        led_expired = self._green_led is not None and self.green_led(now) is None
        if led_expired:
            self._green_led = None
            self._green_led_basis = None
            self._led_on_continuity = False
        fan_expired = self._fan_level_status_confirmed and not self.fan_level_confirmed(
            now
        )
        if fan_expired:
            self._fan_level_status_confirmed = False
        return display_expired or led_expired or fan_expired
