"""Explicit pre-buffer capture: entry isolation, fixed limits and no writes."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
import yaml
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import CONF_EVENT_CAPTURE, DOMAIN, PROFILE
from custom_components.proxon_hesp.diagnostics import async_get_config_entry_diagnostics
from custom_components.proxon_hesp.event_capture import EventCapture
from custom_components.proxon_hesp.services import async_register_services


async def test_trigger_preserves_prebuffer_and_merges_without_extending_window():
    event = EventCapture(True)
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        event.feed(b"before")
        event.observe_rpm(0)
        clock.return_value = 110
        first = event.trigger_diagnostic(" Candidate changed ")
        timer = event.capture.timer
        assert first == {
            "started_utc": event.capture.started,
            "elapsed_ms": 10000,
            "label": "Candidate changed",
            "joined_existing_capture": False,
        }
        assert event.events == [
            {"elapsed_ms": 10000, "type": "diagnostic_trigger", "label": first["label"]}
        ]
        assert event.capture.recording_duration == 190
        clock.return_value = 120
        event.feed(b"after")
        event.observe_rpm(1500)
        second = event.trigger_diagnostic("Second reference")
        assert second["joined_existing_capture"] is True
        assert second["started_utc"] == first["started_utc"]
        assert event.capture.timer is timer
        assert event.capture.recording_duration == 190
        assert event.events[1]["type"] == "compressor_started"
        assert b"".join(bytes.fromhex(c["hex"]) for c in event.capture.chunks) == (
            b"beforeafter"
        )
    event.clear()


async def test_due_timer_is_finished_before_an_explicit_trigger_without_new_data():
    event = EventCapture(True)
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        event.feed(b"before")
        clock.return_value = 110
        event.trigger_diagnostic("First")
        old_timer = event.capture.timer
        clock.return_value = 280
        event.feed(b"recent")
        clock.return_value = 290
        result = event.trigger_diagnostic("After deadline")
        assert result["joined_existing_capture"] is False
        assert old_timer.cancelled()
        assert len(event.previous_captures) == 1
        previous = event.previous_captures[0]
        assert previous["completion_reason"] == "duration_limit"
        assert previous["events"][0]["label"] == "First"
        assert event.events == [
            {
                "elapsed_ms": 10000,
                "type": "diagnostic_trigger",
                "label": "After deadline",
            }
        ]
        assert event.capture.chunks == [{"elapsed_ms": 0, "hex": b"recent".hex()}]
    event.clear()


@pytest.mark.parametrize(
    "label", ["", " ", "x" * 65, "text\n", "text\x00", "text\u202e", 1]
)
async def test_invalid_trigger_does_not_start_or_modify_a_capture(label):
    event = EventCapture(True)
    event.feed(b"buffer")
    with pytest.raises(ValueError, match="invalid_event_label"):
        event.trigger_diagnostic(label)
    assert not event.events and event.capture.timer is None
    assert event.status == "waiting"


async def test_disabled_empty_stale_and_event_limits_preserve_existing_evidence():
    event = EventCapture()
    with pytest.raises(ValueError, match="event_capture_disabled"):
        event.trigger_diagnostic("x")
    event.configure(True)
    with pytest.raises(ValueError, match="event_capture_no_recent_data"):
        event.trigger_diagnostic("x")
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        event.feed(b"before")
        clock.return_value = 130
        with pytest.raises(ValueError, match="event_capture_no_recent_data"):
            event.trigger_diagnostic("x")
        event.feed(b"fresh")
        for number in range(32):
            event.trigger_diagnostic(f"Trigger {number}")
        timer = event.capture.timer
        with pytest.raises(ValueError, match="event_capture_event_limit"):
            event.trigger_diagnostic("Overflow")
        assert len(event.events) == 32 and event.omitted_events == 0
        assert event.capture.timer is timer
    event.clear()


async def test_explicit_windows_keep_existing_four_capture_retention():
    event = EventCapture(True)
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        for number in range(6):
            clock.return_value = number * 400
            event.feed(bytes([number]))
            event.trigger_diagnostic(f"Trigger {number}")
            event.capture.stop("manual")
        export = event.export()
        assert export["capture_count"] == 4
        assert export["overwritten_captures"] == 2
        assert [c["events"][0]["label"] for c in export["previous_captures"]] == [
            "Trigger 2",
            "Trigger 3",
            "Trigger 4",
        ]
        assert export["events"][0]["label"] == "Trigger 5"
    event.clear()


async def test_service_requires_an_explicit_loaded_proxon_entry(hass):
    async_register_services(hass)
    assert hass.services.has_service(DOMAIN, "start_event_capture")
    for target, error in (
        ("missing", "entry_not_found"),
        (DOMAIN, "entry_not_loaded"),
        ("other", "entry_not_found"),
    ):
        entry = MockConfigEntry(domain=target)
        if target != "missing":
            entry.add_to_hass(hass)
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN,
                "start_event_capture",
                {"config_entry_id": entry.entry_id, "label": "x"},
                blocking=True,
            )
        assert err.value.translation_key == error
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "start_event_capture",
            {"label": "x"},
            blocking=True,
        )


async def test_service_isolated_manual_capture_export_and_freshness_without_tx(
    hass, frames
):
    streams, writers = [], []

    async def connect(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(frames["0xe1"])
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        streams.append(reader)
        writers.append(writer)
        return reader, writer

    entries = [
        MockConfigEntry(
            domain=DOMAIN,
            unique_id=f"diagnostic-{index}",
            version=2,
            data={"host": f"unit-{index}.test", "port": 4196, "profile": PROFILE},
            options={CONF_EVENT_CAPTURE: index == 0},
        )
        for index in range(2)
    ]
    for entry in entries:
        entry.add_to_hass(hass)
    with patch("asyncio.open_connection", side_effect=connect) as connector:
        for entry in entries:
            if entry.state is ConfigEntryState.NOT_LOADED:
                assert await hass.config_entries.async_setup(entry.entry_id)
            assert entry.state is ConfigEntryState.LOADED
        await hass.async_block_till_done()
        runtime = entries[0].runtime_data
        runtime.capture.start()
        manual_timer = runtime.capture.timer
        manual_start = runtime.capture.started
        call = {"config_entry_id": entries[0].entry_id, "label": "Candidate changed"}
        result = await hass.services.async_call(
            DOMAIN,
            "start_event_capture",
            call,
            blocking=True,
            return_response=True,
        )
        assert not result["joined_existing_capture"]
        repeated = await hass.services.async_call(
            DOMAIN,
            "start_event_capture",
            call,
            blocking=True,
            return_response=True,
        )
        assert repeated["joined_existing_capture"]
        assert (
            runtime.capture.timer is manual_timer
            and runtime.capture.started == manual_start
        )
        assert (
            runtime.capture.reason == "recording" and not runtime.capture.observations
        )
        export = await async_get_config_entry_diagnostics(hass, entries[0])
        assert export["event_capture"]["events"][0]["type"] == "diagnostic_trigger"
        assert "observations" not in result and "chunks" not in result
        assert not entries[1].runtime_data.event_capture.events
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN,
                "start_event_capture",
                {**call, "config_entry_id": entries[1].entry_id},
                blocking=True,
            )
        assert err.value.translation_key == "event_capture_disabled"
        for key, (reading, stamp) in runtime.values.items():
            runtime.values[key] = (reading, stamp - 31)
        damaged = bytearray(frames["0xe1"])
        damaged[-1] ^= 1
        streams[0].feed_data(damaged)
        await hass.async_block_till_done()
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "start_event_capture", call, blocking=True
            )
        assert err.value.translation_key == "event_capture_no_recent_data"
        assert len(runtime.event_capture.events) == 2
        streams[0].feed_data(frames["0xe1"])
        await hass.async_block_till_done()
        runtime.event_capture.clear()
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "start_event_capture", call, blocking=True
            )
        assert err.value.translation_key == "event_capture_no_recent_data"
        streams[0].feed_data(frames["0xe1"])
        await hass.async_block_till_done()
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "start_event_capture", {**call, "label": "x\n"}, blocking=True
            )
        assert err.value.translation_key == "invalid_event_label"
        assert not runtime.event_capture.events
        await hass.services.async_call(
            DOMAIN, "start_event_capture", call, blocking=True
        )
        streams[0].feed_eof()
        await hass.async_block_till_done()
        assert not runtime.connected
        assert runtime.event_capture.capture.reason == "disconnected"
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "start_event_capture", call, blocking=True
            )
        assert err.value.translation_key == "event_capture_no_recent_data"
        assert entries[0].options == {CONF_EVENT_CAPTURE: True}
        assert entries[1].options == {CONF_EVENT_CAPTURE: False}
        assert connector.call_count == 2  # One existing receiver per entry.
        assert runtime.application_bytes_sent == 0
        for entry in entries:
            assert await hass.config_entries.async_unload(entry.entry_id)
    for writer in writers:
        writer.write.assert_not_called()
        writer.writelines.assert_not_called()


def test_action_fields_and_translations_match_the_runtime_schema():
    base = Path("custom_components/proxon_hesp")
    description = yaml.safe_load((base / "services.yaml").read_text())
    assert set(description["start_event_capture"]["fields"]) == {
        "config_entry_id",
        "label",
    }
    assert set(description["mark_observation"]["fields"]) == {
        "config_entry_id",
        "label",
        "observation",
    }
    for name in ("strings.json", "translations/en.json", "translations/de.json"):
        data = json.loads((base / name).read_text())
        assert set(data["services"]["start_event_capture"]["fields"]) == {
            "config_entry_id",
            "label",
        }
        assert {
            "invalid_event_label",
            "event_capture_disabled",
            "event_capture_no_recent_data",
            "event_capture_event_limit",
        } <= data["exceptions"].keys()
