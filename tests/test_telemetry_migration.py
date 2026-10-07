"""Raw-sensor retirement using HA's real registry and entity lifecycle."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.telemetry_migration import async_retire_raw_sensors


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="migration-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    return entry


def register(registry, entry, key, disabled_by=er.RegistryEntryDisabler.INTEGRATION):
    return registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.unique_id}_{key}",
        config_entry=entry,
        suggested_object_id=f"migration_{key}",
        disabled_by=disabled_by,
    )


async def test_confirmed_duplicates_removed_once_and_other_readings_preserved(
    hass, entry
):
    registry = er.async_get(hass)
    old = [
        register(registry, entry, key)
        for key in (
            "raw_0110",
            "raw_0116",
            "raw_051c",
            "raw_0330",
            "uptime",
            "fan_supply_control",
            "fan_extract_control",
        )
    ]
    replacements = [
        register(registry, entry, key)
        for key in (
            "cooling_threshold",
            "max_heating_output",
            "max_cooling_output",
            "compressor_rpm",
            "device_clock",
            "device_date",
            "fan_supply_control_percent",
            "fan_extract_control_percent",
        )
    ]
    retained = [
        register(registry, entry, key, disabled_by=None)
        for key in ("raw_0105", "device_datetime", "counter_02d4")
    ]

    await async_retire_raw_sensors(hass, entry)
    assert all(registry.async_get(sensor.entity_id) is None for sensor in old)
    assert all(
        registry.async_get(sensor.entity_id) == sensor
        for sensor in (*replacements, *retained)
    )
    remaining = er.async_entries_for_config_entry(registry, entry.entry_id)
    await async_retire_raw_sensors(hass, entry)
    assert er.async_entries_for_config_entry(registry, entry.entry_id) == remaining


@pytest.mark.parametrize(
    "disabled_by",
    [
        None,
        er.RegistryEntryDisabler.INTEGRATION,
        er.RegistryEntryDisabler.USER,
        er.RegistryEntryDisabler.CONFIG_ENTRY,
        er.RegistryEntryDisabler.DEVICE,
    ],
)
async def test_enabled_raw_preserves_replacement_preferences(hass, entry, disabled_by):
    registry = er.async_get(hass)
    old = register(registry, entry, "raw_051c", disabled_by=None)
    replacement = register(registry, entry, "compressor_rpm", disabled_by)
    replacement = registry.async_update_entity(
        replacement.entity_id,
        name="My compressor",
        icon="mdi:air-conditioner",
        hidden_by=er.RegistryEntryHider.USER,
        new_entity_id="sensor.my_existing_compressor",
    )
    replacement = registry.async_update_entity_options(
        replacement.entity_id, "sensor", {"display_precision": 2}
    )

    await async_retire_raw_sensors(hass, entry)
    assert registry.async_get(old.entity_id) is None
    migrated = registry.async_get(replacement.entity_id)
    assert migrated.disabled_by is (
        None if disabled_by is er.RegistryEntryDisabler.INTEGRATION else disabled_by
    )
    assert migrated.entity_id == "sensor.my_existing_compressor"
    assert migrated.name == replacement.name
    assert migrated.icon == replacement.icon
    assert migrated.hidden_by == replacement.hidden_by
    assert migrated.options == replacement.options


@pytest.mark.parametrize(
    "disabled_by",
    [
        er.RegistryEntryDisabler.INTEGRATION,
        er.RegistryEntryDisabler.USER,
        er.RegistryEntryDisabler.CONFIG_ENTRY,
    ],
)
async def test_disabled_raw_keeps_replacement_enablement(hass, entry, disabled_by):
    registry = er.async_get(hass)
    old = register(registry, entry, "raw_0116", disabled_by)
    heating = register(registry, entry, "max_heating_output")
    cooling = register(registry, entry, "max_cooling_output", disabled_by=None)

    await async_retire_raw_sensors(hass, entry)
    assert registry.async_get(old.entity_id) is None
    assert registry.async_get(heating.entity_id) == heating
    assert registry.async_get(cooling.entity_id) == cooling


@pytest.mark.parametrize(
    "raw_key,first_key,missing_key",
    [
        ("raw_0116", "max_heating_output", "max_cooling_output"),
        ("uptime", "device_date", "device_clock"),
    ],
)
async def test_split_retirement_waits_for_all_replacements(
    hass, entry, raw_key, first_key, missing_key
):
    registry = er.async_get(hass)
    old = register(registry, entry, raw_key, disabled_by=None)
    first = register(registry, entry, first_key)

    await async_retire_raw_sensors(hass, entry)
    assert registry.async_get(old.entity_id) == old
    assert registry.async_get(first.entity_id) == first

    second = register(registry, entry, missing_key)
    await async_retire_raw_sensors(hass, entry)
    assert registry.async_get(old.entity_id) is None
    assert registry.async_get(first.entity_id).disabled_by is None
    assert registry.async_get(second.entity_id).disabled_by is None


async def test_foreign_entries_platforms_domains_and_user_entities_are_untouched(
    hass, entry
):
    registry = er.async_get(hass)
    other = MockConfigEntry(domain=DOMAIN, unique_id="other-unit")
    other.add_to_hass(hass)
    own_raw = register(registry, entry, "raw_0110", disabled_by=None)
    foreign_replacement = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.unique_id}_cooling_threshold",
        config_entry=other,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    foreign_raw = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.unique_id}_raw_051c",
        config_entry=other,
        disabled_by=None,
    )
    register(registry, entry, "compressor_rpm")
    binary_raw = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"{entry.unique_id}_raw_0330",
        config_entry=entry,
        disabled_by=None,
    )
    register(registry, entry, "device_clock")
    wrong_platform_raw = registry.async_get_or_create(
        "sensor",
        "other_integration",
        f"{entry.unique_id}_raw_0116",
        config_entry=entry,
        disabled_by=None,
    )
    register(registry, entry, "max_heating_output")
    register(registry, entry, "max_cooling_output")
    user_raw = registry.async_get_or_create(
        "sensor", DOMAIN, f"{entry.unique_id}_uptime", disabled_by=None
    )
    register(registry, entry, "device_date")
    before = list(registry.entities.values())

    await async_retire_raw_sensors(hass, entry)
    assert list(registry.entities.values()) == before
    for retained in (
        own_raw,
        foreign_replacement,
        foreign_raw,
        binary_raw,
        wrong_platform_raw,
        user_raw,
    ):
        assert registry.async_get(retained.entity_id) == retained


async def test_no_unique_identity_does_not_match_none_prefixed_sensors(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=None)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = register(registry, entry, "raw_0110", disabled_by=None)
    replacement = register(registry, entry, "cooling_threshold")

    await async_retire_raw_sensors(hass, entry)
    assert registry.async_get(old.entity_id) == old
    assert registry.async_get(replacement.entity_id) == replacement


async def test_enabled_split_replacements_become_live_and_raw_state_is_removed(
    hass, entry, frames
):
    registry = er.async_get(hass)
    raw = register(registry, entry, "raw_0116", disabled_by=None)
    # Model the unavailable placeholder restored by HA for a removed sensor.
    raw.write_unavailable_state(hass)
    assert hass.states.get(raw.entity_id).attributes["restored"] is True
    controller = json.loads(
        (Path(__file__).parent / "fixtures/controller_frames.json").read_text()
    )
    receivers = []

    @asynccontextmanager
    async def receiver(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(frames["0xe1"] + bytes.fromhex(controller["0x0116"]))
        receivers.append(reader)
        yield reader

    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await async_retire_raw_sensors(hass, entry)
        await hass.async_block_till_done()
        assert registry.async_get(raw.entity_id) is None
        assert hass.states.get(raw.entity_id) is None
        replacement_ids = {
            key: registry.async_get_entity_id(
                "sensor", DOMAIN, f"{entry.unique_id}_{key}"
            )
            for key in ("max_heating_output", "max_cooling_output")
        }
        assert all(
            registry.async_get(entity_id).disabled_by is None
            for entity_id in replacement_ids.values()
        )
        assert len(receivers) == 1
        # Registry updates activate discarded disabled entities via HA's reload.
        future = dt_util.utcnow() + timedelta(seconds=31)
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()
        assert len(receivers) == 2
        assert hass.states.get(replacement_ids["max_heating_output"]).state == "100"
        assert hass.states.get(replacement_ids["max_cooling_output"]).state == "90"
        assert hass.states.get(raw.entity_id) is None

        # Retired entries cannot repeatedly trigger another enablement reload.
        async_fire_time_changed(hass, future + timedelta(seconds=31))
        await hass.async_block_till_done()
        assert len(receivers) == 2

        # A later setup must preserve these enabled sensors and not recreate raw.
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert len(receivers) == 3
        assert registry.async_get(raw.entity_id) is None
        assert hass.states.get(raw.entity_id) is None
        assert hass.states.get(replacement_ids["max_heating_output"]).state == "100"
        assert await hass.config_entries.async_unload(entry.entry_id)
