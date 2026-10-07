"""Retire confirmed raw duplicates after their readable sensors are registered."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

RAW_SENSOR_REPLACEMENTS = {
    "raw_0110": ("cooling_threshold",),
    "raw_0116": ("max_heating_output", "max_cooling_output"),
    "raw_051c": ("compressor_rpm",),
    "raw_0330": ("device_clock",),
    "uptime": ("device_date", "device_clock"),
    "fan_supply_control": ("fan_supply_control_percent",),
    "fan_extract_control": ("fan_extract_control_percent",),
}


async def async_retire_raw_sensors(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove this entry's raw sensors only when all replacements exist.

    A previously enabled raw sensor enables replacements that still have the
    integration's default disablement. Existing user settings are preserved.
    Home Assistant handles state cleanup and the reload needed to activate newly
    enabled entities through its entity-registry events.
    """
    if entry.unique_id is None:
        return

    registry = er.async_get(hass)
    sensors = {
        sensor.unique_id: sensor
        for sensor in er.async_entries_for_config_entry(registry, entry.entry_id)
        if sensor.domain == "sensor" and sensor.platform == DOMAIN
    }
    for raw_key, replacement_keys in RAW_SENSOR_REPLACEMENTS.items():
        raw = sensors.get(f"{entry.unique_id}_{raw_key}")
        if raw is None:
            continue
        replacements = [
            sensors.get(f"{entry.unique_id}_{key}") for key in replacement_keys
        ]
        if any(replacement is None for replacement in replacements):
            continue
        if raw.disabled_by is None:
            for replacement in replacements:
                if (
                    replacement is not None
                    and replacement.disabled_by is er.RegistryEntryDisabler.INTEGRATION
                ):
                    registry.async_update_entity(
                        replacement.entity_id, disabled_by=None
                    )
        registry.async_remove(raw.entity_id)
