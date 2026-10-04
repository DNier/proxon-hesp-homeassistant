"""Bounded annotations follow the capture clock without touching the bus."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.capture import (
    MAX_OBSERVATIONS,
    Capture,
)
from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.diagnostics import async_get_config_entry_diagnostics
from custom_components.proxon_hesp.services import async_register_services
from tools.audit_observations import audit


async def test_markers_share_clock_preserve_snapshots_and_do_not_extend_capture():
    clock = SimpleNamespace(monotonic=lambda: 100.0)
    capture = Capture(30)
    with patch("custom_components.proxon_hesp.capture.time", clock):
        capture.start()
        timer = capture.timer
        clock.monotonic = lambda: 102.125
        capture.feed(b"wire")
        marker = capture.mark_observation(" BDE selection ", " auto ")
        assert marker == {
            "elapsed_ms": 2125,
            "label": "BDE selection",
            "observation": "auto",
        }
        assert capture.chunks[0]["elapsed_ms"] == marker["elapsed_ms"]
        assert capture.timer is timer
        assert capture.recording_duration == 30
        assert capture.export()["format_version"] == 3
        marker["observation"] = "changed"
        snapshot = capture.export()
        snapshot["observations"][0]["observation"] = "changed again"
        assert capture.export()["observations"][0]["observation"] == "auto"
        summary = capture.summary()
        assert summary["observation_count"] == 1
        assert "observations" not in summary
        clock.monotonic = lambda: 130.0
        with pytest.raises(ValueError, match="capture_not_recording"):
            capture.mark_observation("BDE selection", "manual_3")
        assert capture.reason == "duration_limit"
        assert len(capture.observations) == 1
        capture.start()
        assert capture.observations == []
        capture.mark_observation("BDE selection", "auto")
        capture.clear()
        assert capture.export()["observations"] == []


@pytest.mark.parametrize("reason", ["idle", "manual", "disconnected", "byte_limit"])
async def test_no_backdated_or_implicit_capture(reason):
    capture = Capture()
    capture.reason = reason
    with pytest.raises(ValueError, match="capture_not_recording"):
        capture.mark_observation("BDE selection", "auto")
    assert capture.observations == []
    assert capture.timer is None
    assert capture.reason == reason


@pytest.mark.parametrize(
    "label,observation",
    [
        ("", "auto"),
        ("   ", "auto"),
        ("x" * 65, "auto"),
        ("selection", "x" * 161),
        ("selection", ""),
        ("selection", "auto\n"),
        ("selection", "auto\x00"),
        ("selection", "auto\u0085"),
        ("selection", "auto\u2028"),
        ("selection", "auto\u2029"),
        ("selection", "auto\u202e"),
        ("selection\x7f", "auto"),
        (None, "auto"),
        ("selection", 3),
    ],
)
async def test_invalid_annotations_do_not_mutate_capture(label, observation):
    capture = Capture()
    capture.start()
    try:
        with pytest.raises(ValueError, match="invalid_observation"):
            capture.mark_observation(label, observation)
        assert capture.observations == []
    finally:
        capture.clear()


async def test_annotation_limit_is_explicit_and_preserves_existing_references():
    capture = Capture()
    capture.start()
    try:
        capture.mark_observation("x" * 64, "y" * 160)
        for _ in range(MAX_OBSERVATIONS - 1):
            capture.mark_observation("selection", "auto")
        with pytest.raises(ValueError, match="observation_limit"):
            capture.mark_observation("selection", "manual_3")
        assert len(capture.observations) == MAX_OBSERVATIONS
        assert capture.reason == "recording"
    finally:
        capture.clear()


async def test_service_is_available_without_loaded_entry_and_requires_target(hass):
    async_register_services(hass)
    assert hass.services.has_service(DOMAIN, "mark_observation")
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "mark_observation",
            {"config_entry_id": "missing", "label": "selection", "observation": "auto"},
            blocking=True,
        )
    assert err.value.translation_key == "entry_not_found"
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert entry.state is ConfigEntryState.NOT_LOADED
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "mark_observation",
            {
                "config_entry_id": entry.entry_id,
                "label": "selection",
                "observation": "auto",
            },
            blocking=True,
        )
    assert err.value.translation_key == "entry_not_loaded"
    other = MockConfigEntry(domain="other")
    other.add_to_hass(hass)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "mark_observation",
            {
                "config_entry_id": other.entry_id,
                "label": "selection",
                "observation": "auto",
            },
            blocking=True,
        )
    assert err.value.translation_key == "entry_not_found"
    with pytest.raises(vol.Invalid, match="required key"):
        await hass.services.async_call(
            DOMAIN,
            "mark_observation",
            {"label": "selection", "observation": "auto"},
            blocking=True,
        )


async def test_real_service_annotation_export_entry_isolation_and_unload(hass, frames):
    writers = []

    async def connect(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(frames["0xe1"])
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        writers.append(writer)
        return reader, writer

    entries = [
        MockConfigEntry(
            domain=DOMAIN,
            unique_id=f"observer-{index}",
            version=2,
            data={"host": f"unit-{index}.test", "port": 4196, "profile": PROFILE},
        )
        for index in range(2)
    ]
    for entry in entries:
        entry.add_to_hass(hass)
    with patch("asyncio.open_connection", side_effect=connect):
        for entry in entries:
            if entry.state is ConfigEntryState.NOT_LOADED:
                assert await hass.config_entries.async_setup(entry.entry_id)
            assert entry.state is ConfigEntryState.LOADED
        await hass.async_block_till_done()
        call = {
            "config_entry_id": entries[0].entry_id,
            "label": "BDE selection",
            "observation": "auto",
        }
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "mark_observation", call, blocking=True
            )
        assert err.value.translation_key == "capture_not_recording"
        for entry in entries:
            entry.runtime_data.capture.start()
        result = await hass.services.async_call(
            DOMAIN, "mark_observation", call, blocking=True, return_response=True
        )
        assert result["observation"] == "auto"
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN,
                "mark_observation",
                {**call, "observation": "auto\n"},
                blocking=True,
            )
        assert err.value.translation_key == "invalid_observation"
        export = await async_get_config_entry_diagnostics(hass, entries[0])
        assert export["capture"]["observations"] == [result]
        alignment = audit(export["capture"])
        assert alignment["labels"]["BDE selection"]["status"] == (
            "insufficient_references"
        )
        assert export["event_capture"]["observations"] == []
        assert entries[1].runtime_data.capture.observations == []
        assert export["application_bytes_sent"] == 0
        for state in hass.states.async_all():
            assert "observations" not in state.attributes
            assert "observation" not in state.attributes
        for entry in entries:
            assert await hass.config_entries.async_unload(entry.entry_id)
        assert hass.services.has_service(DOMAIN, "mark_observation")
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "mark_observation", call, blocking=True
            )
        assert err.value.translation_key == "entry_not_loaded"
    for writer in writers:
        writer.write.assert_not_called()
        writer.writelines.assert_not_called()
