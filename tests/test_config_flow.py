"""Exercise real HA flow registration, validation and entry creation."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import (
    CONF_CAPTURE_DURATION,
    CONF_EVENT_CAPTURE,
    CONF_P2_REFERENCE_DISPLAY,
    DOMAIN,
    PROFILE,
)
from custom_components.proxon_hesp.hesp.transport import NoSupportedData

INPUT = {"host": "gateway.test", "port": 4196, "name": "PROXON", "profile": PROFILE}


async def test_form_and_create(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    with (
        patch("custom_components.proxon_hesp.config_flow.probe") as probe,
        patch("custom_components.proxon_hesp.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], INPUT
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "gateway.test"
    assert len(result["result"].unique_id) == 32
    probe.assert_awaited_once()


@pytest.mark.parametrize(
    "error,expected",
    [(OSError(), "cannot_connect"), (NoSupportedData(), "no_supported_data")],
)
async def test_errors(hass, error, expected):
    with patch("custom_components.proxon_hesp.config_flow.probe", side_effect=error):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=INPUT
        )
    assert result["errors"] == {"base": expected}


async def test_duplicate_never_opens_second_connection(hass):
    MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id="one").add_to_hass(hass)
    with patch("custom_components.proxon_hesp.config_flow.probe") as probe:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=INPUT
        )
    assert result["reason"] == "already_configured"
    probe.assert_not_called()


async def test_reconfigure_preserves_identity_and_skips_same_endpoint_probe(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, title="Old", unique_id="stable")
    entry.add_to_hass(hass)
    with (
        patch("custom_components.proxon_hesp.config_flow.probe") as probe,
        patch.object(hass.config_entries, "async_reload", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={**INPUT, "name": "New"},
        )
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "stable"
    assert entry.title == "New"
    probe.assert_not_called()


@pytest.mark.parametrize("change_endpoint", [False, True])
async def test_loaded_reconfigure_switches_receiver_only_for_a_new_endpoint(
    hass, frames, change_endpoint
):
    connections = []

    @asynccontextmanager
    async def receiver(host, port, _writer_callback):
        connections.append((host, port))
        reader = asyncio.StreamReader()
        reader.feed_data(frames["0xe1"])
        yield reader

    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, title="Old", unique_id="stable")
    entry.add_to_hass(hass)
    with (
        patch("custom_components.proxon_hesp.config_flow.probe") as probe,
        patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        runtime.capture.start()
        devices = dr.async_get(hass)
        device_id = next(
            iter(dr.async_entries_for_config_entry(devices, entry.entry_id))
        ).id
        changes = {**INPUT, "name": "New"}
        if change_endpoint:
            changes.update(host="new-gateway.test", port=4296)
        async with entry.setup_lock:
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_RECONFIGURE,
                    "entry_id": entry.entry_id,
                },
                data=changes,
            )
            hass.config_entries.async_update_entry(
                entry, options={CONF_CAPTURE_DURATION: 60}
            )
        await hass.async_block_till_done()

        assert result["reason"] == "reconfigure_successful"
        assert devices.async_get(device_id).name == "New"
        assert entry.unique_id == "stable"
        assert entry.runtime_data.capture.duration == 60
        if change_endpoint:
            assert connections == [("gateway.test", 4196), ("new-gateway.test", 4296)]
            assert entry.runtime_data is not runtime
            probe.assert_awaited_once()
        else:
            assert connections == [("gateway.test", 4196)]
            assert entry.runtime_data is runtime
            assert runtime.capture.summary()["status"] == "recording"
            probe.assert_not_called()
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_capture_options_saved_during_setup_apply_without_reconnect(hass, frames):
    reader = asyncio.StreamReader()
    connections = []

    @asynccontextmanager
    async def receiver(host, port, _writer_callback):
        connections.append((host, port))
        reader.feed_data(frames["0xe1"])
        yield reader

    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id="startup-options")
    entry.add_to_hass(hass)

    async def save_options(_hass, _entry):
        assert entry.state is config_entries.ConfigEntryState.SETUP_IN_PROGRESS
        form = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            form["flow_id"], {CONF_CAPTURE_DURATION: 60, CONF_EVENT_CAPTURE: True}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

    with (
        patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver),
        patch(
            "custom_components.proxon_hesp.async_retire_raw_sensors",
            side_effect=save_options,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        try:
            assert entry.runtime_data.capture.duration == 60
            assert entry.runtime_data.event_capture.enabled
            assert connections == [("gateway.test", 4196)]
        finally:
            assert await hass.config_entries.async_unload(entry.entry_id)


async def test_capture_options_default_bounds_and_no_probe(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id="options-unit")
    entry.add_to_hass(hass)
    with patch("custom_components.proxon_hesp.config_flow.probe") as probe:
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["data_schema"]({}) == {
            "capture_duration": 120,
            "event_capture_enabled": False,
            CONF_P2_REFERENCE_DISPLAY: False,
        }
        for invalid in (29, 601, 30.5):
            with pytest.raises(InvalidData):
                await hass.config_entries.options.async_configure(
                    result["flow_id"], {"capture_duration": invalid}
                )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"capture_duration": 600, CONF_P2_REFERENCE_DISPLAY: True},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options["capture_duration"] == 600
        assert entry.options[CONF_P2_REFERENCE_DISPLAY] is True
        assert entry.unique_id == "options-unit"
        probe.assert_not_called()
