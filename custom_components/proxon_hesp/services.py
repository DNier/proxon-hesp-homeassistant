"""Passive, entry-scoped annotations of the current manual capture."""

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

if TYPE_CHECKING:
    from . import ProxonConfigEntry

SERVICE_MARK_OBSERVATION = "mark_observation"
SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("label"): str,
        vol.Required("observation"): str,
    }
)


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register once for the integration, not for individual room devices."""

    async def mark_observation(call: ServiceCall) -> ServiceResponse:
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_found"
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_loaded"
            )
        runtime = cast("ProxonConfigEntry", entry).runtime_data
        try:
            return runtime.capture.mark_observation(
                call.data["label"], call.data["observation"]
            )
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=str(err)
            ) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_OBSERVATION,
        mark_observation,
        schema=SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
