"""Conservative extraction of observed panel and controller values.

Does not claim to decode every HESP frame. Only the exact observed node/type,
length and checksum-validated subset can produce sensor values.
"""

import math
import struct
from dataclasses import dataclass
from datetime import datetime

from .checksum import checksum

MODES = {0: "off", 1: "eco_summer", 2: "eco_winter", 3: "comfort", 4: "stove"}
# Complete status words compared with the display, including Stove mode.
# Do not extract a plausible level from an unverified status word.
CONTROLLER_FAN_LEVELS = {
    0x8000100A: 1,
    0x80001012: 2,
    0x8000101A: 3,
    0x80001022: 4,
    0x80001122: 4,
    0x8000131A: 3,
    0x8200131A: 3,
    0x80001422: 4,
    0x80001522: 4,
    0x8000921A: 3,
    0x8000931A: 3,
}
RAW_POINTS = {
    1310: 4,
    108: 4,
    238: 4,
    360: 1,
    288: 2,
    501: 4,
    272: 4,
    261: 4,
    277: 4,
    284: 4,
    278: 4,
    518: 2,
    1305: 2,
    1308: 4,
    816: 4,
    291: 2,
    527: 2,
    1309: 4,
}
# Exact panel identities keep equal data-point numbers on different nodes apart.
# These payloads have no confirmed PTC or actuator interpretation.
PANEL_RAW_POINTS = {
    b"\x11\x80\x00": {
        0x01F8: ("raw_118000_01f8", 4),
        0x03B6: ("raw_118000_03b6", 4),
    },
    b"\x11\x80\x07": {0x0191: ("raw_118007_0191", 2)},
}
RAW_OBSERVATION_SOURCES = {
    "raw_006c": (b"\x22\x40\x00", 0x006C, 4),
    "raw_0208": (b"\x22\x40\x00", 0x0208, 4),
    **{
        key: (identity, dp, size)
        for identity, points in PANEL_RAW_POINTS.items()
        for dp, (key, size) in points.items()
    },
}

TEMPERATURE_KEYS = (
    "temperature_supply",
    "temperature_extract",
    "temperature_exhaust",
    "temperature_fresh",
    "temperature_before_evaporator",
    "temperature_evaporator",
    "temperature_after_preheater",
    "temperature_before_condenser",
    "temperature_condenser",
    "temperature_compressor",
)

RESPONSE_POINTS = {
    0x00D2: ("fan_supply_curve", 16),
    0x00D3: ("fan_extract_curve", 16),
    0x0208: ("controller_fan_level", 4),
    0x00D7: ("fan_controls", 8),
    0x0160: ("bypass_status", 1),
    0x00C9: ("fan_speeds", 8),
    0x03B7: ("temperatures", 22),
    **{dp: (f"raw_{dp:04x}", size) for dp, size in RAW_POINTS.items()},
    0x00ED: ("filter_days", 4),
    0x032E: ("uptime", 4),
    **{
        dp: (f"counter_{dp:04x}", 4)
        for dp in (0x02D0, 0x02D1, 0x02D2, 0x02D3, 0x02D4, 0x02D5, 0x02D7, 0x02D9)
    },
}

POINTS = {
    0x01F8: ("intensive_ventilation", 4),
    0x00E1: ("fan_level", 2),
    0x020A: ("operating_mode", 2),
    0x0226: ("room_temperature", 4),
    0x0227: ("target_temperature", 4),
}


@dataclass(frozen=True)
class Reading:
    """A verified, typed value from a validated supported frame, not an actuator ACK."""

    key: str
    value: float | int | str | bool


@dataclass
class Statistics:
    bytes_received: int = 0
    accepted: int = 0
    checksum_rejected: int = 0
    checksum_unsupported: int = 0
    value_rejected: int = 0
    discarded_bytes: int = 0


class Decoder:
    """Accept arbitrary TCP boundaries; retain at most one supported candidate."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.stats = Statistics()

    def feed(self, data: bytes) -> list[Reading]:
        self.stats.bytes_received += len(data)
        self.buffer.extend(data)
        readings = []
        while len(self.buffer) >= 8:
            header = self.buffer[:8]
            dp = int.from_bytes(header[3:5], "little")
            identity = bytes(header[:3])
            points = (
                RESPONSE_POINTS
                if identity == b"\x22\x40\x00"
                else POINTS
                if identity == b"\x11\x80\x00"
                else {}
            )
            spec = points.get(dp) or PANEL_RAW_POINTS.get(identity, {}).get(dp)
            if header[5:7] != b"\x00\x00" or spec is None or header[7] != spec[1] * 2:
                del self.buffer[0]
                self.stats.discarded_bytes += 1
                continue
            key, size = spec
            length = 10 + size
            if len(self.buffer) < length:
                break
            frame = bytes(self.buffer[:length])
            calculated = checksum(frame[:-2])
            if calculated is None:
                self.stats.checksum_unsupported += 1
            elif calculated != int.from_bytes(frame[-2:], "little"):
                self.stats.checksum_rejected += 1
            else:
                decoded = self._readings(key, frame[8:-2])
                if decoded:
                    readings.extend(decoded)
                    self.stats.accepted += 1
                else:
                    self.stats.value_rejected += 1
                del self.buffer[:length]
                continue
            # Rescan after a corrupt candidate; never trust its frame boundary.
            del self.buffer[0]
            self.stats.discarded_bytes += 1
        return readings

    @classmethod
    def _readings(cls, key: str, payload: bytes) -> list[Reading]:
        if key in ("fan_supply_curve", "fan_extract_curve"):
            if len(payload) != 16:
                return []
            # Configured stage percentages, not measured airflow or current speed.
            direction = "supply" if key == "fan_supply_curve" else "extract"
            return [
                Reading(f"fan_{direction}_stage_{stage}", value)
                for stage, value in enumerate(struct.unpack("<4f", payload), 1)
                if math.isfinite(value) and 0 <= value <= 100
            ]
        if key == "controller_fan_level":
            # Raw status is evidence, not a validated fan/valve interpretation.
            readings = [
                Reading("experimental_status_0208", payload.hex()),
                Reading("raw_0208", payload.hex()),
            ]
            level = cls._value(key, payload)
            if level is not None:
                readings.append(Reading(key, level))
            return readings
        if key == "fan_controls":
            if len(payload) != 8:
                return []
            # Keep raw controls internally. Sensor presentation validates their
            # factor-100 match against fresh same-direction percent curves.
            return [
                Reading(k, v)
                for k, v in zip(
                    ("fan_supply_control", "fan_extract_control"),
                    struct.unpack("<2f", payload),
                    strict=True,
                )
                if math.isfinite(v) and 0 <= v <= 10000
            ]
        if key == "fan_speeds":
            if len(payload) != 8:
                return []
            values = struct.unpack("<2f", payload)
            return [
                Reading(k, v)
                for k, v in zip(
                    ("fan_supply_rpm", "fan_extract_rpm"), values, strict=True
                )
                if math.isfinite(v) and 0 <= v <= 10000
            ]
        if key == "temperatures":
            if len(payload) != 22:
                return []
            # Signed deci-degrees are supported by negative T6 display evidence.
            # -50..150 C is receive sanity, not a manufacturer operating range.
            # Keep 0xFFFF (-1) excluded: sentinel vs -0.1 C is unresolved.
            values = struct.unpack("<11h", payload)[:10]
            return [
                Reading(k, v / 10)
                for k, v in zip(TEMPERATURE_KEYS, values, strict=True)
                if v != -1 and -500 <= v <= 1500
            ]
        value = cls._value(key, payload)
        if value is None:
            return []
        readings = [Reading(key, value)]
        if key == "raw_0110":
            threshold = struct.unpack("<f", payload)[0]
            # Receive sanity bound only; not a manufacturer setting range.
            if math.isfinite(threshold) and 0 <= threshold <= 100:
                readings.append(Reading("cooling_threshold", threshold))
        if key == "raw_0116":
            readings.extend(
                Reading(name, limit)
                for name, limit in zip(
                    ("max_heating_output", "max_cooling_output"),
                    struct.unpack("<2H", payload),
                    strict=True,
                )
                if limit <= 100
            )
        if key == "intensive_ventilation":
            readings.append(Reading("raw_118000_01f8", payload.hex()))
        if key == "raw_051c":
            # Preserve internal raw evidence, even for invalid numeric data.
            rpm = struct.unpack("<f", payload)[0]
            # Receive sanity bound, not a manufacturer operating limit.
            if math.isfinite(rpm) and 0 <= rpm <= 10000:
                readings.append(Reading("compressor_rpm", rpm))
        if key == "uptime":
            calendar = decode_calendar(payload)
            if calendar is not None:
                readings.append(Reading("device_datetime", calendar))
        if key == "raw_0330":
            clock = decode_clock(payload)
            if clock is not None:
                readings.append(Reading("device_clock", clock))
        return readings

    @staticmethod
    def _value(key: str, payload: bytes) -> float | int | str | bool | None:
        if key == "controller_fan_level":
            return CONTROLLER_FAN_LEVELS.get(int.from_bytes(payload, "little"))
        if key == "bypass_status":
            # Reported BDE switching state; not a measured flap position.
            return bool(payload[0]) if payload[0] in (0, 1) else None
        if key == "intensive_ventilation":
            # BDE request bit: verified at 30/120 min and against manual level 4.
            # Other bits (including observed 0x0800) are independent.
            return bool(int.from_bytes(payload, "little") & 0x40)
        if key.startswith("raw_"):
            return payload.hex()
        if key in ("filter_days", "uptime") or key.startswith("counter_"):
            value = int.from_bytes(payload, "little")
            return value if value != 0xFFFFFFFF else None
        if key == "operating_mode":
            return MODES.get(int.from_bytes(payload, "little"))
        if key == "fan_level":
            level = int.from_bytes(payload, "little")
            return level if 0 <= level <= 4 else None
        value = struct.unpack("<f", payload)[0]
        # The reference BDE supports 18–30 °C; captured 30 °C on 2026-09-14.
        # Retain the existing lower receive bound for other device variants.
        # This plausibility guard is not a writable control's setting range.
        low, high = (15, 30) if key == "target_temperature" else (-20, 60)
        return value if math.isfinite(value) and low <= value <= high else None


def decode_clock(payload: bytes) -> str | None:
    """Observed packed local clock; no date or timezone is inferred."""
    if len(payload) != 4:
        return None
    value = int.from_bytes(payload, "little")
    hour, minute, second = value & 31, (value >> 5) & 63, (value >> 11) & 63
    if value >> 17 or hour > 23 or minute > 59 or second > 59:
        return None
    return f"{hour:02}:{minute:02}:{second:02}"


def decode_calendar(payload: bytes) -> str | None:
    """Observed local calendar, minute resolution; never infer a timezone.

    Keep the legacy raw `uptime` reading separate. A plausible date does not
    establish that the controller clock is synchronized with real time.
    """
    if len(payload) != 4:
        return None
    value = int.from_bytes(payload, "little")
    if value >> 30:
        return None
    minute = value & 63
    hour = (value >> 6) & 31
    weekday = (value >> 11) & 7
    year = 2000 + ((value >> 14) & 127)
    month = (value >> 21) & 15
    day = (value >> 25) & 31
    try:
        calendar = datetime(year, month, day, hour, minute)
    except ValueError:
        return None
    if weekday != (calendar.weekday() + 1) % 7:
        return None
    return calendar.isoformat(timespec="minutes")
