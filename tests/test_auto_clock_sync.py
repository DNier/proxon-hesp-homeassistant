"""Automatic DST clock adjustment through the real HA switch platform."""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.proxon_hesp.const import (
    CONF_AUTO_CLOCK_SYNC,
    CONF_CAPTURE_DURATION,
    CONF_EVENT_CAPTURE,
    DOMAIN,
    PROFILE,
)
from custom_components.proxon_hesp.hesp.calendar import calendar_frame, calendar_payload
from custom_components.proxon_hesp.hesp.checksum import checksum

BERLIN_SPRING = datetime.fromisoformat("2027-03-28T02:15:00+00:00")
BERLIN_FALL = datetime.fromisoformat("2027-10-31T03:15:00+00:00")


def calendar_response(payload):
    body = bytes.fromhex("2240002e03000008") + payload
    return body + checksum(body).to_bytes(2, "little")


@asynccontextmanager
async def configured_switch(
    hass, freezer, *, start, calendar, zone="Europe/Berlin", enabled=None
):
    freezer.move_to(start)
    await hass.config.async_set_time_zone(zone)
    opts = {CONF_CAPTURE_DURATION: 120, CONF_EVENT_CAPTURE: True}
    if enabled is not None:
        opts[CONF_AUTO_CLOCK_SYNC] = enabled
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="dst-clock-unit",
        title="PROXON",
        options=opts,
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    streams = []

    async def connect(*_args):
        reader = asyncio.StreamReader()
        reader.feed_data(calendar_response(calendar_payload(calendar)))
        writer = MagicMock()
        writer.is_closing.return_value = False
        writer.drain = AsyncMock()
        writer.wait_closed = AsyncMock()
        streams.append((reader, writer))
        return reader, writer

    with patch("asyncio.open_connection", side_effect=connect):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_id = registry.async_get_entity_id(
            "switch", DOMAIN, f"{entry.unique_id}_auto_clock_sync"
        )
        assert entity_id is not None
        streams[0][1].write.assert_not_called()
        try:
            yield entry, entity_id, streams
        finally:
            assert await hass.config_entries.async_unload(entry.entry_id)


async def fire_time(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, instant)
    await hass.async_block_till_done()
    for _ in range(8):
        await asyncio.sleep(0)


async def turn(hass, entity_id, action):
    await hass.services.async_call(
        "switch", action, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("zone", "due", "old_clock_offset"),
    [
        ("Europe/Berlin", BERLIN_SPRING, -60),
        ("Europe/Berlin", BERLIN_FALL, 60),
        (
            "Australia/Lord_Howe",
            datetime.fromisoformat("2027-10-02T17:15:00+00:00"),
            -30,
        ),
    ],
)
async def test_scheduled_dst_check_confirms_one_clock_write(
    hass, freezer, zone, due, old_clock_offset
):
    local = due.astimezone(ZoneInfo(zone))
    async with configured_switch(
        hass,
        freezer,
        start=due - timedelta(seconds=10),
        calendar=local + timedelta(minutes=old_clock_offset),
        zone=zone,
        enabled=True,
    ) as (entry, entity_id, streams):
        assert hass.states.is_state(entity_id, "on")
        reader, writer = streams[0]
        writer.write.side_effect = lambda frame: reader.feed_data(
            calendar_response(frame[8:12])
        )
        await fire_time(hass, freezer, due)
        writer.write.assert_called_once_with(calendar_frame(local))
        assert entry.runtime_data.clock_sync_status == "confirmed"
        assert entry.runtime_data.application_bytes_sent == len(calendar_frame(local))
        assert len(streams) == 1


@pytest.mark.parametrize(
    ("case", "due", "zone", "clock_offset"),
    [
        ("off", BERLIN_SPRING, "Europe/Berlin", -60),
        ("ordinary day", BERLIN_SPRING + timedelta(days=1), "Europe/Berlin", -60),
        ("no DST", BERLIN_SPRING + timedelta(hours=2), "UTC", -60),
        ("wrong sign", BERLIN_SPRING, "Europe/Berlin", 60),
        ("wrong magnitude", BERLIN_SPRING, "Europe/Berlin", -57),
        ("already aligned", BERLIN_SPRING, "Europe/Berlin", 0),
        ("stale", BERLIN_SPRING, "Europe/Berlin", -60),
    ],
)
async def test_schedule_skips_ineligible_calendar(
    hass, freezer, case, due, zone, clock_offset
):
    local = due.astimezone(ZoneInfo(zone))
    async with configured_switch(
        hass,
        freezer,
        start=due - timedelta(seconds=10),
        calendar=local + timedelta(minutes=clock_offset),
        zone=zone,
        enabled=None if case == "off" else True,
    ) as (entry, entity_id, streams):
        runtime = entry.runtime_data
        _, writer = streams[0]
        if case == "stale":
            for key in ("uptime", "device_datetime"):
                reading, _ = runtime.values[key]
                runtime.values[key] = reading, time.monotonic() - 31
        assert hass.states.is_state(entity_id, "off" if case == "off" else "on")
        await fire_time(hass, freezer, due)
        writer.write.assert_not_called()
        assert runtime.application_bytes_sent == 0


@pytest.mark.parametrize("invalid_payload", ["00000000", "ffffffff"])
async def test_latest_invalid_calendar_blocks_sync(hass, freezer, invalid_payload):
    due = BERLIN_SPRING
    local = due.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass,
        freezer,
        start=due - timedelta(seconds=10),
        calendar=local - timedelta(hours=1),
        enabled=True,
    ) as (entry, _, streams):
        runtime = entry.runtime_data
        reader, writer = streams[0]
        assert runtime.decoder.last_calendar_valid is True
        reader.feed_data(calendar_response(bytes.fromhex(invalid_payload)))
        await hass.async_block_till_done()
        assert runtime.decoder.last_calendar_valid is False
        await fire_time(hass, freezer, due)
        writer.write.assert_not_called()
        assert runtime.application_bytes_sent == 0


async def test_switch_persists_preference_without_reloading(hass, freezer):
    start = BERLIN_SPRING - timedelta(minutes=1)
    local = start.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass,
        freezer,
        start=start,
        calendar=local,
    ) as (entry, entity_id, streams):
        registry = er.async_get(hass)
        switch = registry.async_get(entity_id)
        assert switch.disabled_by is None
        assert switch.entity_category == "config"
        for platform, key in (("sensor", "device_datetime"), ("button", "clock_sync")):
            optional = registry.async_get_entity_id(
                platform, DOMAIN, f"{entry.unique_id}_{key}"
            )
            assert (
                registry.async_get(optional).disabled_by
                is er.RegistryEntryDisabler.INTEGRATION
            )
        assert hass.states.is_state(entity_id, "off")
        initial_options = dict(entry.options)
        runtime = entry.runtime_data

        await turn(hass, entity_id, "turn_on")
        assert hass.states.is_state(entity_id, "on")
        assert entry.options == {**initial_options, CONF_AUTO_CLOCK_SYNC: True}
        assert runtime.clock_sync_status == "already_current"
        await turn(hass, entity_id, "turn_off")
        assert hass.states.is_state(entity_id, "off")
        assert entry.options == {**initial_options, CONF_AUTO_CLOCK_SYNC: False}
        assert entry.runtime_data is runtime
        assert len(streams) == 1
        streams[0][1].write.assert_not_called()

        await turn(hass, entity_id, "turn_on")
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert len(streams) == 2
        assert entry.runtime_data is not runtime
        assert entry.runtime_data.clock_sync_status == "idle"
        assert hass.states.is_state(entity_id, "on")
        for _, writer in streams:
            writer.write.assert_not_called()


async def test_restoring_opt_in_at_scheduled_instant_does_not_send(hass, freezer):
    due = BERLIN_SPRING
    local = due.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass,
        freezer,
        start=due,
        calendar=local - timedelta(hours=1),
        enabled=True,
    ) as (entry, entity_id, streams):
        assert hass.states.is_state(entity_id, "on")
        await fire_time(hass, freezer, due)
        streams[0][1].write.assert_not_called()
        assert entry.runtime_data.application_bytes_sent == 0


@pytest.mark.parametrize("offset", [timedelta(), timedelta(days=1, hours=2)])
async def test_switch_on_aligns_clock_once_at_check_time_or_on_ordinary_day(
    hass, freezer, offset
):
    activation = BERLIN_SPRING + offset
    local = activation.astimezone(ZoneInfo("Europe/Berlin"))
    old = calendar_response(calendar_payload(local - timedelta(hours=1)))
    async with configured_switch(
        hass,
        freezer,
        start=activation - timedelta(seconds=10),
        calendar=local - timedelta(hours=1),
    ) as (entry, entity_id, streams):
        reader, writer = streams[0]
        writer.write.side_effect = lambda frame: reader.feed_data(
            calendar_response(frame[8:12])
        )
        freezer.move_to(activation)
        await turn(hass, entity_id, "turn_on")
        assert entry.options[CONF_AUTO_CLOCK_SYNC] is True
        assert hass.states.is_state(entity_id, "on")
        assert entry.runtime_data.clock_sync_status == "confirmed"
        writer.write.assert_called_once_with(calendar_frame(local))

        # Keep a matching DST deviation visible again to prove the scheduled
        # check cannot make a second write at activation time.
        reader.feed_data(old)
        await hass.async_block_till_done()
        await fire_time(hass, freezer, activation)
        await turn(hass, entity_id, "turn_off")
        assert hass.states.is_state(entity_id, "off")
        writer.write.assert_called_once_with(calendar_frame(local))


@pytest.mark.parametrize("stale_or_invalid", ["stale", "00000000", "ffffffff"])
async def test_switch_on_persists_without_valid_calendar(
    hass, freezer, stale_or_invalid
):
    now = BERLIN_SPRING + timedelta(hours=3)
    local = now.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass, freezer, start=now, calendar=local - timedelta(hours=1)
    ) as (entry, entity_id, streams):
        runtime = entry.runtime_data
        reader, writer = streams[0]
        if stale_or_invalid == "stale":
            for key in ("uptime", "device_datetime"):
                reading, _ = runtime.values[key]
                runtime.values[key] = reading, time.monotonic() - 31
        else:
            reader.feed_data(calendar_response(bytes.fromhex(stale_or_invalid)))
            await hass.async_block_till_done()
            assert runtime.decoder.last_calendar_valid is False
        await turn(hass, entity_id, "turn_on")
        assert entry.options[CONF_AUTO_CLOCK_SYNC] is True
        assert hass.states.is_state(entity_id, "on")
        writer.write.assert_not_called()
        assert runtime.application_bytes_sent == 0


async def test_unconfirmed_activation_is_not_repeated_or_retried_by_schedule(
    hass, freezer
):
    due = BERLIN_SPRING
    activation = due - timedelta(seconds=45)
    local = activation.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass, freezer, start=activation, calendar=local - timedelta(hours=1)
    ) as (entry, entity_id, streams):
        reader, writer = streams[0]
        writer.drain.side_effect = OSError("Fake gateway error")
        await turn(hass, entity_id, "turn_on")
        assert entry.options[CONF_AUTO_CLOCK_SYNC] is True
        assert hass.states.is_state(entity_id, "on")
        assert entry.runtime_data.clock_sync_status == "unconfirmed"
        writer.write.assert_called_once_with(calendar_frame(local))

        # Keep the connection and a valid but offset calendar fresh. By the
        # repeat and the scheduled check the writer's 30 s cooldown has elapsed.
        await fire_time(hass, freezer, due - timedelta(seconds=20))
        reader.feed_data(
            calendar_response(calendar_payload(local - timedelta(hours=1)))
        )
        await hass.async_block_till_done()
        await fire_time(hass, freezer, due - timedelta(seconds=5))
        await turn(hass, entity_id, "turn_on")
        await fire_time(hass, freezer, due)
        assert entry.runtime_data.connected
        writer.write.assert_called_once_with(calendar_frame(local))


async def test_no_retry_after_failed_write(hass, freezer):
    due = BERLIN_SPRING
    local = due.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass,
        freezer,
        start=due - timedelta(seconds=10),
        calendar=local - timedelta(hours=1),
        enabled=True,
    ) as (entry, entity_id, streams):
        reader, writer = streams[0]
        writer.drain.side_effect = OSError("Fake gateway error")
        await fire_time(hass, freezer, due)
        writer.write.assert_called_once_with(calendar_frame(local))
        assert entry.runtime_data.clock_sync_status == "unconfirmed"
        reader.feed_data(
            calendar_response(calendar_payload(local - timedelta(hours=1)))
        )
        await hass.async_block_till_done()
        await turn(hass, entity_id, "turn_off")
        await fire_time(hass, freezer, due + timedelta(seconds=10))
        writer.write.assert_called_once_with(calendar_frame(local))


async def test_reconnect_does_not_catch_up_missed_check(hass, freezer):
    due = BERLIN_SPRING
    local = due.astimezone(ZoneInfo("Europe/Berlin"))
    async with configured_switch(
        hass,
        freezer,
        start=due - timedelta(seconds=10),
        calendar=local - timedelta(hours=1),
        enabled=True,
    ) as (entry, _, streams):
        freezer.move_to(due - timedelta(milliseconds=200))
        streams[0][0].feed_eof()
        await hass.async_block_till_done()
        assert not entry.runtime_data.connected
        await fire_time(hass, freezer, due)
        assert len(streams) == 1
        await fire_time(hass, freezer, due + timedelta(seconds=5))
        assert len(streams) == 2
        assert entry.runtime_data.connected
        assert entry.runtime_data.application_bytes_sent == 0
        for _, writer in streams:
            writer.write.assert_not_called()
