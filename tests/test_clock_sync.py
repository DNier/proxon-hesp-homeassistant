"""Explicit one-shot calendar write, confirmation and failure boundaries."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.coordinator import ProxonRuntime
from custom_components.proxon_hesp.hesp.calendar import calendar_frame
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Reading

UNSET = bytes.fromhex("2240002e030000080cc022022bcb")
TARGET = bytes.fromhex("1180002e03000008999b262fba84")


def response(payload):
    body = bytes.fromhex("2240002e03000008") + payload
    return body + checksum(body).to_bytes(2, "little")


def test_encoder_matches_recorded_successful_write():
    local = datetime(2026, 9, 23, 14, 25, tzinfo=ZoneInfo("Europe/Berlin"))
    assert calendar_frame(local) == TARGET
    with pytest.raises(ValueError):
        calendar_frame(local.replace(tzinfo=None))
    with pytest.raises(ValueError):
        calendar_frame(local.replace(year=2128))


@pytest.mark.parametrize("next_minute", [False, True])
async def test_button_uses_existing_connection_and_waits_for_calendar(
    hass, freezer, next_minute
):
    freezer.move_to("2026-09-23T12:25:00+00:00")
    await hass.config.async_set_time_zone("Europe/Berlin")
    reader = asyncio.StreamReader()
    reader.feed_data(UNSET)
    writer = MagicMock()
    writer.is_closing.return_value = False
    writer.drain = AsyncMock()
    written = asyncio.Event()
    writer.write.side_effect = lambda _: written.set()
    writer.wait_closed = AsyncMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="clock-unit",
        title="PROXON",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    button = registry.async_get_or_create(
        "button", DOMAIN, "clock-unit_clock_sync", config_entry=entry, disabled_by=None
    )
    with patch("asyncio.open_connection", return_value=(reader, writer)) as connect:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        writer.write.assert_not_called()
        task = asyncio.create_task(
            hass.services.async_call(
                "button", "press", {"entity_id": button.entity_id}, blocking=True
            )
        )
        await written.wait()
        writer.write.assert_called_once_with(TARGET)
        connect.assert_called_once()
        # An ACK and an unchanged raw calendar must not confirm the command.
        body = bytes.fromhex("2340002e03000000")
        reader.feed_data(body + checksum(body).to_bytes(2, "little") + UNSET)
        for _ in range(10):
            await asyncio.sleep(0)
        assert not task.done()
        assert entry.runtime_data.clock_sync_status == "waiting"
        assert entry.runtime_data.diagnostics()["clock_bytes_attempted"] == 14
        assert entry.runtime_data.diagnostics()["clock_bytes_confirmed"] == 0
        # The final calendar receipt in a single read supersedes a transient match.
        reader.feed_data(response(TARGET[8:12]) + UNSET)
        for _ in range(10):
            await asyncio.sleep(0)
        assert not task.done()
        assert entry.runtime_data.diagnostics()["clock_bytes_confirmed"] == 0
        payload = (int.from_bytes(TARGET[8:12], "little") + int(next_minute)).to_bytes(
            4, "little"
        )
        reader.feed_data(response(payload))
        await task
        assert entry.runtime_data.clock_sync_status == "confirmed"
        assert entry.runtime_data.diagnostics()["application_bytes_sent"] == 14
        assert entry.runtime_data.diagnostics()["clock_bytes_confirmed"] == 14
        assert await hass.config_entries.async_unload(entry.entry_id)
        writer.write.assert_called_once()
        writer.close.assert_called_once()


def runtime(hass):
    import time

    r = ProxonRuntime(hass, "gateway.test", 4196)
    r.connected = True
    r.values["uptime"] = (Reading("uptime", 35831820), time.monotonic())
    r.writer = MagicMock()
    r.writer.is_closing.return_value = False
    r.writer.drain = AsyncMock()
    return r


@pytest.mark.parametrize("condition", ["disconnected", "stale", "closing"])
async def test_unavailable_does_not_send(hass, condition):
    r = runtime(hass)
    if condition == "disconnected":
        r.connected = False
    elif condition == "stale":
        reading, timestamp = r.values["uptime"]
        r.values["uptime"] = (reading, timestamp - 31)
    else:
        r.writer.is_closing.return_value = True
    with pytest.raises(HomeAssistantError):
        await r.sync_clock()
    r.writer.write.assert_not_called()


async def test_already_current_does_not_send(hass, freezer):
    freezer.move_to("2026-09-23T12:25:00+00:00")
    await hass.config.async_set_time_zone("Europe/Berlin")
    r = runtime(hass)
    r.values["uptime"] = (
        Reading("uptime", int.from_bytes(TARGET[8:12], "little")),
        r.values["uptime"][1],
    )
    await r.sync_clock()
    assert r.clock_sync_status == "already_current"
    r.writer.write.assert_not_called()


async def test_calendar_is_rechecked_after_writer_drain(hass, freezer):
    freezer.move_to("2026-09-23T12:25:00+00:00")
    await hass.config.async_set_time_zone("Europe/Berlin")
    r = runtime(hass)
    started = asyncio.Event()
    drained = asyncio.Event()
    r.writer.write.side_effect = lambda _: started.set()
    r.writer.drain.side_effect = drained.wait

    task = asyncio.create_task(r.sync_clock())
    await started.wait()
    previous = r.values["uptime"]
    r.values["uptime"] = (
        Reading("uptime", int.from_bytes(TARGET[8:12], "little")),
        previous[1],
    )
    r._clock_pending.set_result(True)
    r.values["uptime"] = previous
    drained.set()

    with pytest.raises(HomeAssistantError, match="time update unconfirmed"):
        await task
    r.writer.write.assert_called_once_with(TARGET)
    assert r.diagnostics()["clock_bytes_attempted"] == 14
    assert r.diagnostics()["clock_bytes_confirmed"] == 0


@pytest.mark.parametrize("same_chunk", [True, False], ids=["same-read", "during-drain"])
async def test_invalid_calendar_after_matching_receipt_cannot_confirm(hass, same_chunk):
    await hass.config.async_set_time_zone("Europe/Berlin")
    local = datetime(2026, 9, 23, 14, 25, tzinfo=ZoneInfo("Europe/Berlin"))
    reader = asyncio.StreamReader()
    reader.feed_data(UNSET)
    writer = MagicMock()
    writer.is_closing.return_value = False
    drained = asyncio.Event()
    writer.drain = AsyncMock(side_effect=drained.wait)
    writer.wait_closed = AsyncMock()
    written = asyncio.Event()
    writer.write.side_effect = lambda _: written.set()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="invalid-clock-unit",
        title="PROXON",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    timeout = asyncio.timeout
    with (
        patch("asyncio.open_connection", return_value=(reader, writer)),
        patch("custom_components.proxon_hesp.coordinator.datetime") as clock,
    ):
        clock.now.side_effect = lambda zone: local.astimezone(zone)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        r = entry.runtime_data
        with patch(
            "custom_components.proxon_hesp.coordinator.asyncio.timeout",
            side_effect=lambda seconds: timeout(0.05 if seconds == 20 else seconds),
        ):
            task = asyncio.create_task(r.sync_clock())
            try:
                await written.wait()
                matching = response(TARGET[8:12])
                invalid = response(bytes.fromhex("ffffffff"))
                if same_chunk:
                    reader.feed_data(matching + invalid)
                else:
                    reader.feed_data(matching)
                    for _ in range(10):
                        await asyncio.sleep(0)
                    assert r._clock_pending.done()
                    assert not task.done()
                    reader.feed_data(invalid)
                for _ in range(10):
                    await asyncio.sleep(0)
                assert r.decoder.last_calendar_valid is False
                if same_chunk:
                    assert not r._clock_pending.done()
                # The rejected raw value deliberately leaves the last good cache.
                assert r.get("uptime").value == int.from_bytes(TARGET[8:12], "little")
                drained.set()
                with pytest.raises(HomeAssistantError, match="time update unconfirmed"):
                    await task
                assert r.clock_sync_status == "unconfirmed"
                assert r._clock_pending is None
                assert r.diagnostics()["application_bytes_sent"] == 14
                assert r.diagnostics()["clock_bytes_attempted"] == 14
                assert r.diagnostics()["clock_bytes_confirmed"] == 0
                writer.write.assert_called_once_with(TARGET)
                with pytest.raises(HomeAssistantError, match="30 seconds"):
                    await r.sync_clock()
                writer.write.assert_called_once()
            finally:
                drained.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "failure", ["timeout", "disconnect", "cancel", "drain", "write"]
)
async def test_failures_never_retry_and_release_pending(hass, failure):
    r = runtime(hass)
    writer = r.writer
    written = asyncio.Event()

    def write(_):
        written.set()
        if failure == "write":
            raise OSError("private endpoint")

    writer.write.side_effect = write
    if failure == "drain":
        writer.drain.side_effect = OSError("private endpoint")
    timeout = asyncio.timeout
    with patch(
        "custom_components.proxon_hesp.coordinator.asyncio.timeout",
        side_effect=lambda _: timeout(0.02 if failure == "timeout" else 10),
    ):
        task = asyncio.create_task(r.sync_clock())
        await written.wait()
        if failure == "disconnect":
            r._set_writer(None)
        elif failure == "cancel":
            task.cancel()
        with pytest.raises(
            asyncio.CancelledError if failure == "cancel" else HomeAssistantError
        ):
            await task
    assert r._clock_pending is None
    assert r.clock_sync_status == "unconfirmed"
    assert r.diagnostics()["application_bytes_sent"] == (
        0 if failure == "write" else 14
    )
    assert r.diagnostics()["clock_bytes_attempted"] == 14
    assert r.diagnostics()["clock_bytes_confirmed"] == 0
    writer.write.assert_called_once()
    if failure != "disconnect":
        with pytest.raises(HomeAssistantError, match="30 seconds"):
            await r.sync_clock()
    writer.write.assert_called_once()


async def test_double_press_is_rejected_without_queue(hass):
    r = runtime(hass)
    written = asyncio.Event()
    r.writer.write.side_effect = lambda _: written.set()
    task = asyncio.create_task(r.sync_clock())
    await written.wait()
    with pytest.raises(HomeAssistantError, match="already in progress"):
        await r.sync_clock()
    r._set_writer(None)
    with pytest.raises(HomeAssistantError):
        await task
