"""Recording status, options and upgrades through real HA entities."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.diagnostics import async_get_config_entry_diagnostics
from tools.compare_captures import compare
from tools.inventory_capture import inventory
from tools.replay_diagnosis import replay

MANIFEST_VERSION = json.loads(
    Path("custom_components/proxon_hesp/manifest.json").read_text()
)["version"]


@pytest.fixture
async def diagnostic_setup(hass, frames):
    streams = []

    async def connect(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(frames["0xe1"])
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        streams.append((reader, writer))
        return reader, writer

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="diagnostic-unit",
        version=1,
        data={"host": "private.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    # Enable optional diagnostics before setup, without a reload.
    for domain, key in (
        ("sensor", "last_valid_received"),
        ("binary_sensor", "connection"),
    ):
        registry.async_get_or_create(
            domain, DOMAIN, f"diagnostic-unit_{key}", config_entry=entry
        )
    with patch("asyncio.open_connection", side_effect=connect):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        ids = {
            e.unique_id.removeprefix("diagnostic-unit_"): e.entity_id
            for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        yield entry, streams, ids
        runtime = entry.runtime_data
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.timer is None and runtime.task is None
        assert runtime.capture.timer is None
        assert runtime.event_capture.capture.timer is None
        assert not runtime.event_capture.ring
        assert not runtime.listeners and not runtime.diagnostic_listeners
        for _, writer in streams:
            writer.write.assert_not_called()
            writer.writelines.assert_not_called()
            writer.close.assert_called_once()


async def press(hass, ids, action):
    await hass.services.async_call(
        "button", "press", {"entity_id": ids[f"capture_{action}"]}, blocking=True
    )


async def test_status_timer_without_traffic_and_no_raw_attributes(
    hass, diagnostic_setup
):
    entry, streams, ids = diagnostic_setup
    runtime = entry.runtime_data

    def state():
        return hass.states.get(ids["capture_status"])

    assert state().state == "idle"
    assert hass.states.get(ids["connection"]).state == "on"
    assert hass.states.get(ids["last_valid_received"]).state not in (
        "unknown",
        "unavailable",
    )
    # Shorten only the scheduling interval; exercise the real timer -> HA path.
    with patch.object(runtime.capture, "duration", 0.02):
        await press(hass, ids, "start")
        assert state().state == "recording"
        await asyncio.sleep(0.04)
        await hass.async_block_till_done()
    assert state().state == "duration_limit"
    assert state().attributes["actual_duration_seconds"] >= 0.02
    assert state().attributes["stopped_utc"] is not None
    assert state().attributes["bytes"] == 0
    assert "chunks" not in state().attributes
    duration = state().attributes["actual_duration_seconds"]
    await press(hass, ids, "stop")
    assert state().attributes["actual_duration_seconds"] == duration
    await press(hass, ids, "clear")
    assert state().state == "idle"
    assert state().attributes["started_utc"] is None
    assert len(streams) == 1


async def test_options_preserve_active_capture_and_export_compatibility(
    hass, diagnostic_setup, frames
):
    entry, streams, ids = diagnostic_setup
    runtime = entry.runtime_data
    await press(hass, ids, "start")
    streams[0][0].feed_data(frames["0xe1"])
    await hass.async_block_till_done()
    timer = runtime.capture.timer
    chunks = runtime.capture.export()["chunks"]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"capture_duration": 600}
    )
    await hass.async_block_till_done()
    assert entry.runtime_data is runtime
    assert runtime.capture.timer is timer
    assert runtime.capture.export()["chunks"] == chunks
    assert runtime.capture.recording_duration == 120
    assert runtime.capture.duration == 600
    assert len(streams) == 1
    await press(hass, ids, "stop")
    export = await async_get_config_entry_diagnostics(hass, entry)
    version = MANIFEST_VERSION
    assert export["integration_version"] == version
    assert export["capture"]["integration_version"] == version
    assert export["capture"]["profile"] == PROFILE
    assert "private.test" not in str(export)
    assert "diagnostic-unit" not in str(export)
    assert export["capture"]["format_version"] == 2
    assert inventory(export["capture"]["chunks"])["frames"] == 1
    raw = b"".join(bytes.fromhex(c["hex"]) for c in chunks)
    assert replay(raw)["readings"]["fan_level"]["last"] == 3
    legacy = {"format_version": 1, "chunks": chunks, "duration_seconds": 120}
    assert compare(legacy, export["capture"])["groups"]["118000/0x00E1/2"][
        "same_observed_sequence"
    ]
    assert "chunks" not in hass.states.get(ids["capture_status"]).attributes
    await press(hass, ids, "start")
    assert runtime.capture.recording_duration == 600
    assert not runtime.capture.chunks
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.capture.duration == 600
    assert runtime.capture.timer is None
    assert not runtime.diagnostic_listeners
    assert hass.states.get(ids["capture_status"]).state == "idle"


async def test_disconnect_visible_and_invalid_bytes_do_not_refresh_timestamp(
    hass, diagnostic_setup
):
    entry, streams, ids = diagnostic_setup
    runtime = entry.runtime_data
    last_valid = runtime.last_valid_received
    await press(hass, ids, "start")
    streams[0][0].feed_data(b"not a supported frame")
    await hass.async_block_till_done()
    assert runtime.last_valid_received == last_valid
    assert runtime.capture.size > 0
    # Ordinary bus data never emits recording attributes at chunk frequency.
    assert hass.states.get(ids["capture_status"]).attributes["bytes"] == 0
    streams[0][0].feed_eof()
    await hass.async_block_till_done()
    assert hass.states.get(ids["capture_status"]).state == "disconnected"
    assert hass.states.get(ids["capture_status"]).attributes["bytes"] > 0
    assert hass.states.get(ids["connection"]).state == "off"
    assert hass.states.get(ids["fan_level"]).state == "unavailable"
    assert runtime.last_valid_received == last_valid


@pytest.mark.parametrize(
    "limit,reason", [("MAX_BYTES", "byte_limit"), ("MAX_CHUNKS", "chunk_limit")]
)
async def test_memory_limit_updates_status_immediately(
    hass, diagnostic_setup, limit, reason
):
    entry, streams, ids = diagnostic_setup
    await press(hass, ids, "start")
    with patch(f"custom_components.proxon_hesp.capture.{limit}", 1):
        streams[0][0].feed_data(b"unknown")
        await hass.async_block_till_done()
    assert hass.states.get(ids["capture_status"]).state == reason
    assert entry.runtime_data.capture.timer is None
    assert "chunks" not in hass.states.get(ids["capture_status"]).attributes


def test_translations_cover_all_capture_states_and_diagnostics():
    from custom_components.proxon_hesp.capture import STATUSES

    root = Path("custom_components/proxon_hesp")
    source = json.loads((root / "strings.json").read_text())
    assert source == json.loads((root / "translations/en.json").read_text())
    for filename in ("strings.json", "translations/de.json"):
        data = json.loads((root / filename).read_text())
        assert set(data["entity"]["sensor"]["capture_status"]["state"]) == set(STATUSES)
        assert data["entity"]["sensor"]["last_valid_received"]["name"]
        assert data["entity"]["binary_sensor"]["connection"]["name"]
        assert data["options"]["step"]["init"]["data"]["capture_duration"]


async def test_automatic_capture_uses_validated_stream_and_preserves_manual(
    hass, diagnostic_setup, frames, tmp_path
):
    from tests.test_operating_telemetry import HEATING, STOPPED
    from tools.inventory_capture import load_capture

    entry, streams, ids = diagnostic_setup
    runtime = entry.runtime_data
    reader = streams[0][0]
    assert hass.states.get(ids["event_capture_status"]).state == "disabled"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"capture_duration": 120, "event_capture_enabled": True}
    )
    await hass.async_block_till_done()
    assert entry.runtime_data is runtime and len(streams) == 1
    assert hass.states.get(ids["event_capture_status"]).state == "waiting"
    await press(hass, ids, "start")
    reader.feed_data(STOPPED)
    await hass.async_block_till_done()
    damaged = bytearray(HEATING)
    damaged[-1] ^= 1
    reader.feed_data(damaged)
    await hass.async_block_till_done()
    assert runtime.event_capture.status == "waiting"
    reader.feed_data(HEATING[:9])
    await hass.async_block_till_done()
    assert runtime.event_capture.status == "waiting"
    reader.feed_data(HEATING[9:])
    await hass.async_block_till_done()
    assert hass.states.get(ids["event_capture_status"]).state == "recording"
    assert runtime.capture.reason == "recording"
    await press(hass, ids, "stop")
    manual = runtime.capture.export()
    reader.feed_data(STOPPED)
    await hass.async_block_till_done()
    runtime.event_capture.capture.stop("duration_limit")
    await hass.async_block_till_done()
    assert hass.states.get(ids["event_capture_status"]).state == "ready"
    assert "chunks" not in hass.states.get(ids["event_capture_status"]).attributes
    assert "events" not in hass.states.get(ids["event_capture_status"]).attributes
    export = await async_get_config_entry_diagnostics(hass, entry)
    assert export["event_capture"]["events"][0]["type"] == "compressor_started"
    assert export["event_capture"]["events"][1]["type"] == "compressor_stopped"
    chunks = export["event_capture"]["chunks"]
    raw = b"".join(bytes.fromhex(c["hex"]) for c in chunks)
    assert raw == STOPPED + damaged + HEATING + STOPPED
    assert replay(raw)["readings"]["compressor_rpm"]["count"] == 3
    path = tmp_path / "diagnostic.json"
    path.write_text(json.dumps({"data": export}))
    assert load_capture(path, event=True)["chunks"] == chunks
    assert load_capture(path)["chunks"] == manual["chunks"]
    # Retained first event cannot be overwritten by subsequent transitions.
    reader.feed_data(HEATING + STOPPED)
    await hass.async_block_till_done()
    assert runtime.event_capture.export()["chunks"] == chunks
    assert runtime.capture.export() == manual
    await hass.services.async_call(
        "button", "press", {"entity_id": ids["event_capture_clear"]}, blocking=True
    )
    assert runtime.event_capture.status == "waiting"
    assert runtime.capture.export() == manual
    reader.feed_data(HEATING)  # New baseline, not a false start.
    await hass.async_block_till_done()
    assert not runtime.event_capture.events
    reader.feed_data(STOPPED)
    await hass.async_block_till_done()
    reader.feed_eof()
    await hass.async_block_till_done()
    assert runtime.event_capture.capture.reason == "disconnected"
    assert runtime.event_capture.capture.timer is None
    assert runtime.diagnostics()["application_bytes_sent"] == 0
