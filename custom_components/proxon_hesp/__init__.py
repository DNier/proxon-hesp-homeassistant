"""Local PROXON HESP reception and optional device time correction."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigSubentry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .capture import DURATION, validate_duration
from .const import (
    CONF_CAPTURE_DURATION,
    CONF_EVENT_CAPTURE,
    CONF_P2_REFERENCE_DISPLAY,
    CONF_PROFILE,
    DEVICE_MODEL,
    DOMAIN,
    P2_DEVICE_MODEL,
    PROFILE,
)
from .coordinator import ProxonRuntime
from .rooms import CONF_ROOMS, ROOM_SUBENTRY, configured_rooms, sync_room_devices
from .services import async_register_services
from .telemetry_migration import async_retire_raw_sensors

type ProxonConfigEntry = ConfigEntry[ProxonRuntime]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SWITCH]


def _sync_main_device(hass: HomeAssistant, entry: ProxonConfigEntry) -> None:
    """Apply the hardware selection to the runtime and its registry device."""
    p2_selected = entry.options.get(CONF_P2_REFERENCE_DISPLAY) is True
    entry.runtime_data.configure_p2_reference_display(p2_selected)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        manufacturer="Zimmermann",
        model=P2_DEVICE_MODEL if p2_selected else DEVICE_MODEL,
    )


def _apply_entry_options(hass: HomeAssistant, entry: ProxonConfigEntry) -> None:
    runtime = entry.runtime_data
    runtime.capture.duration = validate_duration(
        entry.options.get(CONF_CAPTURE_DURATION, DURATION)
    )
    runtime.event_capture.configure(entry.options.get(CONF_EVENT_CAPTURE, False))
    _sync_main_device(hass, entry)
    runtime._notify_diagnostics()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Keep diagnostic actions discoverable even while entries are unloaded."""
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    if entry.data.get(CONF_PROFILE) != PROFILE:
        return False
    integration = await async_get_integration(hass, DOMAIN)
    runtime = ProxonRuntime(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        capture_duration=entry.options.get(CONF_CAPTURE_DURATION, DURATION),
        event_capture_enabled=entry.options.get(CONF_EVENT_CAPTURE, False),
        integration_version=str(integration.version),
        profile=entry.data[CONF_PROFILE],
        p2_reference_display=entry.options.get(CONF_P2_REFERENCE_DISPLAY) is True,
    )
    try:
        await runtime.start(entry)
    except TimeoutError as err:
        raise ConfigEntryNotReady("No supported HESP data received") from err
    entry.runtime_data = runtime
    try:
        _sync_main_device(hass, entry)
        sync_room_devices(hass, entry)
        runtime.room_config = configured_rooms(entry)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        await async_retire_raw_sensors(hass, entry)
        # Options can change before the loaded entry starts listening for updates.
        _apply_entry_options(hass, entry)
    except BaseException:
        await runtime.stop()
        raise
    entry.async_on_unload(entry.add_update_listener(async_update_entry))
    return True


async def async_update_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> None:
    """Reconnect for endpoint changes and apply other updates in place."""
    if entry.state is not ConfigEntryState.LOADED:
        return
    runtime = entry.runtime_data
    async with runtime.config_update_lock:
        if (
            entry.state is not ConfigEntryState.LOADED
            or entry.runtime_data is not runtime
        ):
            return
        endpoint = entry.data[CONF_HOST], entry.data[CONF_PORT]
        if (runtime.host, runtime.port) != endpoint:
            # Keep other entry updates behind this reload until the runtime changes.
            await hass.config_entries.async_reload(entry.entry_id)
            return

        _apply_entry_options(hass, entry)
        rooms = configured_rooms(entry)
        if rooms != runtime.room_config:
            for update in runtime.room_updates:
                await update()
            sync_room_devices(hass, entry, runtime.room_config)
            runtime.room_config = rooms


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.stop()
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Move beta room options to subentries without changing room identities."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        existing = {sub.unique_id for sub in entry.subentries.values()}
        for room in entry.options.get(CONF_ROOMS, []):
            if room["id"] not in existing:
                hass.config_entries.async_add_subentry(
                    entry,
                    ConfigSubentry(
                        data=MappingProxyType(dict(room)),
                        subentry_type=ROOM_SUBENTRY,
                        title=room["name"],
                        unique_id=room["id"],
                    ),
                )
                existing.add(room["id"])
        options = dict(entry.options)
        options.pop(CONF_ROOMS, None)
        hass.config_entries.async_update_entry(entry, options=options, version=2)
    return True
