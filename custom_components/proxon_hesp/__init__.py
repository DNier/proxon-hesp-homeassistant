"""Read-only local PROXON HESP reception."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_PROFILE, PROFILE
from .coordinator import ProxonRuntime

type ProxonConfigEntry = ConfigEntry[ProxonRuntime]
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    if entry.data.get(CONF_PROFILE) != PROFILE:
        return False
    runtime = ProxonRuntime(hass, entry.data[CONF_HOST], entry.data[CONF_PORT])
    try:
        await runtime.start(entry)
    except TimeoutError as err:
        raise ConfigEntryNotReady("No supported HESP data received") from err
    entry.runtime_data = runtime
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await runtime.stop()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.stop()
    return unloaded
