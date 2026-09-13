"""Conservative extraction of observed panel and controller values.

Does not claim to decode every HESP frame. Only the exact observed node/type,
length and checksum-validated subset can produce sensor values.
"""

import math
import struct
from dataclasses import dataclass

from .checksum import checksum

MODES = {0: "off", 1: "eco_summer", 2: "eco_winter", 3: "comfort", 4: "stove"}
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

RESPONSE_POINTS = {
    **{dp: (f"raw_{dp:04x}", size) for dp, size in RAW_POINTS.items()},
    0x00ED: ("filter_days", 4),
    0x032E: ("uptime", 4),
    **{
        dp: (f"counter_{dp:04x}", 4)
        for dp in (0x02D0, 0x02D1, 0x02D2, 0x02D3, 0x02D4, 0x02D5, 0x02D7, 0x02D9)
    },
}

POINTS = {
    0x00E1: ("fan_level", 2),
    0x020A: ("operating_mode", 2),
    0x0226: ("room_temperature", 4),
    0x0227: ("target_temperature", 4),
}


@dataclass(frozen=True)
class Reading:
    """A verified, typed value from a validated supported frame, not an actuator ACK."""

    key: str
    value: float | int | str


@dataclass
class Statistics:
    bytes_received: int = 0
    accepted: int = 0
    checksum_rejected: int = 0
    checksum_unsupported: int = 0
    value_rejected: int = 0
    discarded_bytes: int = 0


class Decoder:
    """Accept arbitrary TCP boundaries; retain at most one short candidate."""

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
            points = RESPONSE_POINTS if header[:3] == b"\x22\x40\x00" else POINTS
            spec = points.get(dp)
            if (
                header[:3] not in (b"\x11\x80\x00", b"\x22\x40\x00")
                or header[5:7] != b"\x00\x00"
                or spec is None
                or header[7] != spec[1] * 2
            ):
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
                value = self._value(key, frame[8:-2])
                if value is not None:
                    readings.append(Reading(key, value))
                    self.stats.accepted += 1
                else:
                    self.stats.value_rejected += 1
                del self.buffer[:length]
                continue
            # Rescan after a corrupt candidate; never trust its frame boundary.
            del self.buffer[0]
            self.stats.discarded_bytes += 1
        return readings

    @staticmethod
    def _value(key: str, payload: bytes) -> float | int | str | None:
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
        low, high = (15, 25) if key == "target_temperature" else (-20, 60)
        return value if math.isfinite(value) and low <= value <= high else None
