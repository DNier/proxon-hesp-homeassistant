"""Calendar display references, malformed fields and HA availability."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder, decode_calendar

# Minimal recorded responses matched to BDE calendar editing; no capture metadata.
VALID = bytes.fromhex("2240002e03000008329b262f5880")
UNSET = bytes.fromhex("2240002e030000080cc022022bcb")


def test_recorded_calendar_fragmentation_and_raw_identity():
    for split in range(len(VALID) + 1):
        decoder = Decoder()
        readings = decoder.feed(VALID[:split]) + decoder.feed(VALID[split:])
        assert {r.key: r.value for r in readings} == {
            "uptime": 791059250,
            "device_datetime": "2026-09-23T12:50",
        }
    assert {r.key: r.value for r in Decoder().feed(UNSET)} == {
        "uptime": int.from_bytes(UNSET[8:12], "little")
    }
    damaged = VALID[:-1] + bytes([VALID[-1] ^ 1])
    assert Decoder().feed(damaged) == []
    # A BDE write must not be treated as a controller calendar response.
    body = bytes.fromhex("1180002e03000008329b262f")
    assert Decoder().feed(body + checksum(body).to_bytes(2, "little")) == []


def packed(year, month, day, hour, minute, weekday):
    return (
        minute
        | hour << 6
        | weekday << 11
        | (year - 2000) << 14
        | month << 21
        | day << 25
    ).to_bytes(4, "little")


@pytest.mark.parametrize(
    "year,month,day,hour,minute,weekday",
    [
        (2024, 2, 29, 23, 59, 4),
        (2000, 2, 29, 0, 0, 2),
        (2011, 1, 1, 0, 12, 6),  # Year 2011 alone is not an invalid value.
        (2026, 12, 31, 23, 59, 4),
        (2027, 1, 1, 0, 0, 5),
    ],
)
def test_calendar_boundaries(year, month, day, hour, minute, weekday):
    assert decode_calendar(packed(year, month, day, hour, minute, weekday)) == (
        datetime(year, month, day, hour, minute).isoformat(timespec="minutes")
    )


@pytest.mark.parametrize(
    "fields",
    [
        (2026, 2, 29, 12, 0, 0),
        (2100, 2, 29, 12, 0, 1),
        (2026, 4, 31, 12, 0, 5),
        (2026, 0, 1, 12, 0, 4),
        (2026, 13, 1, 12, 0, 4),
        (2026, 1, 0, 12, 0, 4),
        (2026, 1, 1, 24, 0, 4),
        (2026, 1, 1, 12, 60, 4),
        (2026, 1, 1, 12, 0, 7),
        (2026, 1, 1, 12, 0, 3),
    ],
)
def test_invalid_calendar_fields(fields):
    assert decode_calendar(packed(*fields)) is None


@pytest.mark.parametrize("payload", [b"", bytes(3), bytes(5), bytes(4), b"\xff" * 4])
def test_invalid_calendar_shape_and_sentinels(payload):
    assert decode_calendar(payload) is None


@pytest.mark.parametrize("bit", [30, 31])
def test_unverified_upper_bits(bit):
    value = int.from_bytes(VALID[8:12], "little") | 1 << bit
    assert decode_calendar(value.to_bytes(4, "little")) is None


async def test_enabled_calendar_local_text_freshness_and_disconnect(hass):
    reader = asyncio.StreamReader()
    reader.feed_data(UNSET)  # Establish transport with no valid interpreted date.

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="calendar-unit",
        title="PROXON",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    saved = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "calendar-unit_device_datetime",
        config_entry=entry,
        disabled_by=None,
    )
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(saved.entity_id).state == "unavailable"
        reader.feed_data(VALID)
        await hass.async_block_till_done()
        state = hass.states.get(saved.entity_id)
        assert state.state == "2026-09-23T12:50"
        for key in ("device_class", "unit_of_measurement", "state_class"):
            assert key not in state.attributes
        runtime = entry.runtime_data
        previous = runtime.values["device_datetime"]
        reader.feed_data(UNSET)
        await hass.async_block_till_done()
        assert runtime.values["device_datetime"] == previous
        # Invalid calendar updates cannot keep the interpreted value fresh.
        reading, timestamp = previous
        runtime.values["device_datetime"] = (reading, timestamp - 31)
        runtime._notify()
        assert hass.states.get(saved.entity_id).state == "unavailable"
        assert runtime.get("uptime") is not None
        reader.feed_data(VALID)
        await hass.async_block_till_done()
        assert hass.states.get(saved.entity_id).state == "2026-09-23T12:50"
        reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.get(saved.entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)
