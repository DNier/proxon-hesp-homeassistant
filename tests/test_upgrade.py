"""Upgrade from the 0.8.0 registry contract without changing identities."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE

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
        elif item["key"] == "raw_0116":
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

    @asynccontextmanager
    async def receiver(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(b"".join(frames.values()))
        yield reader

    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data.capture.duration == 120
        assert not entry.options
        for unique_id, (entity_id, disabled) in baseline.items():
            current = registry.async_get(entity_id)
            assert current.unique_id == unique_id
            assert current.disabled_by == disabled
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
        assert len(all_entities) == 57
        new = {
            e.unique_id.removeprefix("existing-unit_"): e
            for e in all_entities
            if e.unique_id not in baseline
        }
        assert set(new) == {"capture_status", "last_valid_received", "connection"}
        assert new["capture_status"].disabled_by is None
        for key in ("last_valid_received", "connection"):
            assert new[key].disabled_by == er.RegistryEntryDisabler.INTEGRATION
        assert await hass.config_entries.async_unload(entry.entry_id)
