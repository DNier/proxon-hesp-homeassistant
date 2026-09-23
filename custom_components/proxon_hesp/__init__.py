"""Read-only local PROXON HESP reception."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_integration

from .capture import DURATION, validate_duration
from .const import (
    CONF_CAPTURE_DURATION,
    CONF_EVENT_CAPTURE,
    CONF_PROFILE,
    DOMAIN,
    PROFILE,
)
from .coordinator import ProxonRuntime
from .rooms import CONF_ROOMS, sync_room_devices

type ProxonConfigEntry = ConfigEntry[ProxonRuntime]
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


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
    )
    try:
        await runtime.start(entry)
    except TimeoutError as err:
        raise ConfigEntryNotReady("No supported HESP data received") from err
    entry.runtime_data = runtime
    sync_room_devices(hass, entry)
    runtime.room_config = entry.options.get(CONF_ROOMS, [])
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await runtime.stop()
        raise
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ProxonConfigEntry) -> None:
    """Apply to the next recording without reloading or losing the current one."""
    entry.runtime_data.capture.duration = validate_duration(
        entry.options.get(CONF_CAPTURE_DURATION, DURATION)
    )
    entry.runtime_data.event_capture.configure(
        entry.options.get(CONF_EVENT_CAPTURE, False)
    )
    entry.runtime_data._notify_diagnostics()
    rooms = entry.options.get(CONF_ROOMS, [])
    if rooms != entry.runtime_data.room_config:
        for update in entry.runtime_data.room_updates:
            await update()
        sync_room_devices(hass, entry, entry.runtime_data.room_config)
        entry.runtime_data.room_config = rooms


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.stop()
    return unloaded
