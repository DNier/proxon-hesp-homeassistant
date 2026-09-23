"""Only the display-verified calendar SET; no arbitrary write API."""

from datetime import datetime

from .checksum import checksum


def calendar_payload(local: datetime) -> bytes:
    """Encode local calendar fields; seconds and UTC offset are not transmitted."""
    if local.tzinfo is None or local.utcoffset() is None:
        raise ValueError("An explicit local timezone is required")
    if not 2000 <= local.year <= 2127:
        raise ValueError("Year outside the calendar field range")
    value = (
        local.minute
        | local.hour << 6
        | ((local.weekday() + 1) % 7) << 11
        | (local.year - 2000) << 14
        | local.month << 21
        | local.day << 25
    )
    return value.to_bytes(4, "little")


def calendar_frame(local: datetime) -> bytes:
    body = bytes.fromhex("1180002e03000008") + calendar_payload(local)
    return body + checksum(body).to_bytes(2, "little")
