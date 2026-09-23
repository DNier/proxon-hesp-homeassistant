"""Real HA sensors and registry backed by an in-memory passive TCP stream."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.diagnostics import async_get_config_entry_diagnostics


async def test_setup_values_availability_registry_and_unload(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(b"".join(frames.values()))
    controller = json.loads(
        (Path(__file__).parent / "fixtures/controller_frames.json").read_text()
    )
    reader.feed_data(b"".join(bytes.fromhex(frame) for frame in controller.values()))
    closed = asyncio.Event()

    @asynccontextmanager
    async def receiver(*args):
        try:
            yield reader
        finally:
            closed.set()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="stable-unit",
        data={"host": "private.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        fan_id = registry.async_get_entity_id("sensor", DOMAIN, "stable-unit_fan_level")
        mode_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_operating_mode"
        )
        assert hass.states.get(fan_id).state == "3"
        assert hass.states.get(mode_id).state == "eco_summer"
        device = dr.async_get(hass).async_get(registry.async_get(fan_id).device_id)
        filter_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_filter_days"
        )
        assert hass.states.get(filter_id).state == "114"
        assert hass.states.get(filter_id).attributes["unit_of_measurement"] == "d"
        raw_id = registry.async_get_entity_id("sensor", DOMAIN, "stable-unit_raw_0116")
        assert registry.async_get(raw_id).disabled_by is not None
        assert hass.states.get(raw_id) is None
        clock_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_device_clock"
        )
        assert registry.async_get(clock_id).disabled_by is not None
        assert hass.states.get(clock_id) is None
        hours_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_counter_02d4"
        )
        assert hass.states.get(hours_id).state == "26708"
        assert hass.states.get(hours_id).attributes["unit_of_measurement"] == "h"
        assert hass.states.get(hours_id).attributes["device_class"] == "duration"
        uptime_id = registry.async_get_entity_id("sensor", DOMAIN, "stable-unit_uptime")
        assert (
            registry.async_get(uptime_id).disabled_by
            == er.RegistryEntryDisabler.INTEGRATION
        )
        assert hass.states.get(uptime_id) is None
        assert registry.async_get(filter_id).entity_category.value == "diagnostic"
        assert "state_class" not in hass.states.get(hours_id).attributes
        assert device.model == "PROXON P-Serie (HESP)"
        assert len(er.async_entries_for_config_entry(registry, entry.entry_id)) == 65
        for key in (
            "device_datetime",
            "controller_fan_level",
            "fan_supply_control",
            "fan_extract_control",
        ):
            diagnostic_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"stable-unit_{key}"
            )
            diagnostic = registry.async_get(diagnostic_id)
            assert diagnostic.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            assert diagnostic.entity_category.value == "diagnostic"
            assert diagnostic.device_id == device.id
            assert hass.states.get(diagnostic_id) is None
        new_ids = []
        from custom_components.proxon_hesp.hesp.decoder import TEMPERATURE_KEYS

        for key in (
            *TEMPERATURE_KEYS,
            "fan_supply_rpm",
            "fan_extract_rpm",
            "compressor_rpm",
        ):
            entity_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"stable-unit_{key}"
            )
            registered = registry.async_get(entity_id)
            assert registered.device_id == device.id
            if key not in TEMPERATURE_KEYS[:4]:
                assert registered.disabled_by == er.RegistryEntryDisabler.INTEGRATION
                assert registered.entity_category.value == "diagnostic"
                assert hass.states.get(entity_id) is None
                continue
            new_ids.append(entity_id)
            assert registered.disabled_by is None
            assert registered.entity_category is None
            state = hass.states.get(entity_id)
            assert state.state not in ("unavailable", "unknown")
            assert state.attributes["state_class"] == "measurement"
            assert state.attributes["unit_of_measurement"] == (
                "°C" if key in TEMPERATURE_KEYS else "rpm"
            )
            if key in TEMPERATURE_KEYS:
                assert state.attributes["device_class"] == "temperature"
        runtime = entry.runtime_data
        start_id = registry.async_get_entity_id(
            "button", DOMAIN, "stable-unit_capture_start"
        )
        await hass.services.async_call(
            "button", "press", {"entity_id": start_id}, blocking=True
        )
        reader.feed_data(b"unrecognized_capture_data")
        await hass.async_block_till_done()
        assert (
            runtime.capture.export()["chunks"][0]["hex"]
            == b"unrecognized_capture_data".hex()
        )
        runtime.capture.clear()
        # One value expires while another remains fresh.
        reading, timestamp = runtime.values["fan_level"]
        runtime.values["fan_level"] = (reading, timestamp - 31)
        runtime._notify()
        assert hass.states.get(fan_id).state == "unavailable"
        assert hass.states.get(mode_id).state == "eco_summer"
        diagnostic = await async_get_config_entry_diagnostics(hass, entry)
        assert "private.test" not in str(diagnostic)
        assert "stable-unit" not in str(diagnostic)
        assert diagnostic["application_bytes_sent"] == 0
        assert diagnostic["statistics"]["accepted"] == 37
        reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.get(mode_id).state == "unavailable"
        assert all(
            hass.states.get(entity_id).state == "unavailable" for entity_id in new_ids
        )
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.task is None
        assert runtime.timer is None
        assert closed.is_set()
