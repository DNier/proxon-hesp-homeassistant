"""Diagnostics deliberately exclude endpoint, identifiers and raw payloads."""

from homeassistant.core import HomeAssistant

from . import ProxonConfigEntry
from .const import CONF_PROFILE


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ProxonConfigEntry
) -> dict:
    return {
        "profile": entry.data[CONF_PROFILE],
        **entry.runtime_data.diagnostics(),
    }
