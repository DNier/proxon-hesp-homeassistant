"""Upgrade from 0.8.0: retire raw duplicates, preserve other identities/settings."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.telemetry_migration import RAW_SENSOR_REPLACEMENTS

BASELINE = json.loads(
    (Path(__file__).parent / "fixtures/registry_0_8_0.json").read_text()
)


async def test_0_8_0_registry_settings_and_default_options_survive(hass, frames):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Existing PROXON",
        unique_id="existing-unit",
        version=1,
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    baseline = {}
    for item in BASELINE["entries"]:
        disabled = (
            None if item["enabled_default"] else er.RegistryEntryDisabler.INTEGRATION
        )
        # Both a user-disabled default sensor and a user-enabled raw sensor.
        if item["key"] == "temperature_supply":
            disabled = er.RegistryEntryDisabler.USER
        elif item["key"] in {"raw_0115", "raw_0116", "raw_0120"}:
            disabled = None
        saved = registry.async_get_or_create(
            item["domain"],
            DOMAIN,
            f"existing-unit_{item['key']}",
            config_entry=entry,
            suggested_object_id=f"existing_{item['key']}",
            disabled_by=disabled,
        )
        assert saved.entity_id == item["entity_id"]
        if item["key"] == "fan_level":
            registry.async_update_entity(saved.entity_id, name="Custom ventilation")
        baseline[saved.unique_id] = (saved.entity_id, disabled)
    assert len(baseline) == 54
    enabled_replacements = {
        key
        for raw_key, keys in RAW_SENSOR_REPLACEMENTS.items()
        if baseline[f"existing-unit_{raw_key}"][1] is None
        for key in keys
    }
    controller_frames = json.loads(
        (Path(__file__).parent / "fixtures/controller_frames.json").read_text()
    )

    @asynccontextmanager
    async def receiver(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(
            b"".join(frames.values())
            + bytes.fromhex(controller_frames["0x0115"])
            + bytes.fromhex("22400020010000041e004d60")
        )
        yield reader

    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data.capture.duration == 120
        assert not entry.options
        for unique_id, (entity_id, disabled) in baseline.items():
            current = registry.async_get(entity_id)
            if unique_id.removeprefix("existing-unit_") in RAW_SENSOR_REPLACEMENTS:
                assert current is None
                assert hass.states.get(entity_id) is None
                continue
            assert current.unique_id == unique_id
            key = unique_id.removeprefix("existing-unit_")
            assert current.disabled_by == (
                None
                if key in enabled_replacements
                and disabled == er.RegistryEntryDisabler.INTEGRATION
                else disabled
            )
            if unique_id.endswith(
                ("temperature_compressor", "compressor_rpm", "filter_days")
            ):
                assert current.entity_category.value == "diagnostic"
        assert (
            registry.async_get("sensor.existing_fan_level").name == "Custom ventilation"
        )
        assert hass.states.get("sensor.existing_fan_level").state == "3"
        assert hass.states.get("sensor.existing_temperature_supply") is None
        for item in BASELINE["entries"]:
            if (state := hass.states.get(item["entity_id"])) is not None and item[
                "domain"
            ] == "sensor":
                assert state.attributes.get("unit_of_measurement") == item["unit"]
        all_entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert len(all_entities) == 81
        new = {
            e.unique_id.removeprefix("existing-unit_"): e
            for e in all_entities
            if e.unique_id not in baseline
        }
        assert set(new) == {
            "compressor_command_percent",
            "bde_operating_display",
            "bde_green_led",
            "cooling_threshold",
            "heat_pump_start_threshold",
            "heat_pump_continuous_run_threshold",
            "fan_supply_control_percent",
            "fan_extract_control_percent",
            "max_heating_output",
            "max_cooling_output",
            "fan_supply_stage_1",
            "fan_supply_stage_2",
            "fan_supply_stage_3",
            "fan_supply_stage_4",
            "fan_extract_stage_1",
            "fan_extract_stage_2",
            "fan_extract_stage_3",
            "fan_extract_stage_4",
            "experimental_0208_bit_8",
            "experimental_0208_bit_9",
            "experimental_0208_bit_28",
            "heat_cool_valve",
            "defrost_valve",
            "clock_sync",
            "auto_clock_sync",
            "device_datetime",
            "device_date",
            "capture_status",
            "last_valid_received",
            "connection",
            "compressor_running",
            "event_capture_status",
            "event_capture_clear",
            "raw_118000_01f8",
            "raw_118000_03b6",
            "raw_118007_0191",
            "raw_0208",
        }
        assert new["compressor_running"].disabled_by is None
        assert new["capture_status"].disabled_by is None
        assert hass.states.is_state(new["auto_clock_sync"].entity_id, "off")
        # Enabled raw_0116 carries visibility to both meaningful limit sensors.
        assert new["max_heating_output"].disabled_by is None
        assert new["max_cooling_output"].disabled_by is None
        heat_pump_start = new["heat_pump_start_threshold"]
        assert heat_pump_start.disabled_by is None
        command = new["compressor_command_percent"]
        assert command.disabled_by is None
        # HA reloads the entry after the registry enables its replacement.
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
        await hass.async_block_till_done()
        heat_pump_start_state = hass.states.get(heat_pump_start.entity_id)
        assert round(float(heat_pump_start_state.state), 1) == 0.4
        assert heat_pump_start_state.attributes["unit_of_measurement"] == "K"
        command_state = hass.states.get(command.entity_id)
        assert command_state.state == "30"
        assert command_state.attributes["unit_of_measurement"] == "%"
        assert "state_class" not in command_state.attributes
        runtime = entry.runtime_data
        reading, received_at = runtime.values["compressor_command_percent"]
        runtime.values["compressor_command_percent"] = (reading, received_at - 31)
        runtime._notify()
        assert hass.states.get(command.entity_id).state == "unavailable"
        assert new["device_date"].disabled_by is None
        for key in (
            "bde_operating_display",
            "bde_green_led",
            "cooling_threshold",
            "heat_pump_continuous_run_threshold",
            "fan_supply_control_percent",
            "fan_extract_control_percent",
            "fan_supply_stage_1",
            "fan_supply_stage_2",
            "fan_supply_stage_3",
            "fan_supply_stage_4",
            "fan_extract_stage_1",
            "fan_extract_stage_2",
            "fan_extract_stage_3",
            "fan_extract_stage_4",
            "last_valid_received",
            "connection",
            "device_datetime",
            "experimental_0208_bit_8",
            "experimental_0208_bit_9",
            "experimental_0208_bit_28",
            "heat_cool_valve",
            "defrost_valve",
            "clock_sync",
            "raw_118000_01f8",
            "raw_118000_03b6",
            "raw_118007_0191",
            "raw_0208",
        ):
            assert new[key].disabled_by == er.RegistryEntryDisabler.INTEGRATION
        assert await hass.config_entries.async_unload(entry.entry_id)
