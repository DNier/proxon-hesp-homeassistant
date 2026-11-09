"""Shared validation of inventory observations, without parsing wire bytes."""

import re

_IDENTITY = re.compile(
    r"([a-f0-9]{6})/0x([0-9A-F]{4}(?:[0-9A-F]{4})?)/(0|[1-9][0-9]{0,2})"
)
_HEX = re.compile(r"(?:[a-fA-F0-9]{2})*")
METADATA_POINTS = frozenset((0x0033, 0x0034, 0x0038, 0x0039))


def integer(value, name, *, minimum=0, maximum=None):
    """Validate a bounded integer without accepting booleans as numbers."""
    if (
        type(value) is not int
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise ValueError(f"{name} must be an integer in its allowed range")
    return value


def frames(report):
    """Yield the existing normalized inventory rows in validated wire order."""
    rows = report.get("frame_observations")
    if not isinstance(rows, list):
        raise ValueError("inventory requires include_frame_observations=True")
    previous_time = previous_index = previous_unparsed = -1
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid frame observation")
        identity = row.get("identity")
        match = _IDENTITY.fullmatch(identity) if isinstance(identity, str) else None
        if match is None:
            raise ValueError("invalid frame identity")
        header, register, size = match.groups()
        register_id = int(register, 16)
        selector = register_id >> 16
        if len(register) == 8 and not selector:
            raise ValueError(
                "zero-selector identity must retain the legacy four-digit DP"
            )
        size = int(size)
        raw = row.get("payload_hex")
        if (
            size > 128
            or not isinstance(raw, str)
            or _HEX.fullmatch(raw) is None
            or len(raw) != size * 2
        ):
            raise ValueError("payload does not match frame identity")
        if selector and not (
            register_id & 0xFFFF in METADATA_POINTS
            and (
                (header == "108000" and size == 2 and raw.lower() == "0100")
                or (header == "224000" and size == 128)
            )
        ):
            raise ValueError(
                "unsupported selector-bearing metadata identity or payload"
            )
        time = integer(row.get("elapsed_ms"), "frame elapsed_ms")
        index = integer(row.get("frame_index"), "frame_index")
        unparsed = integer(row.get("unparsed_bytes_before"), "unparsed_bytes_before")
        if (
            time < previous_time
            or index <= previous_index
            or unparsed < previous_unparsed
        ):
            raise ValueError("frame observations must preserve monotonic wire order")
        previous_time, previous_index, previous_unparsed = time, index, unparsed
        yield {
            # Only the five inventory fields are input. Never trust caller-supplied
            # derived IDs/offsets (including a one-field pair) over the identity.
            "identity": identity,
            "elapsed_ms": time,
            "frame_index": index,
            "unparsed_bytes_before": unparsed,
            "header": header,
            "dp": register_id & 0xFFFF,
            **(
                {"register_id": register_id, "selector_offset": selector}
                if selector
                else {}
            ),
            "payload_bytes": size,
            "payload_hex": raw.lower(),
        }
