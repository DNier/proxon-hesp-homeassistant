"""Entry-scoped passive recording actions; never send to the device."""

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
SERVICE_START_EVENT_CAPTURE = "start_event_capture"
SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("label"): str,
        vol.Required("observation"): str,
    }
)
EVENT_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("label"): str,
    }
)


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register once for the integration, not for individual room devices."""

    def runtime_for_call(call: ServiceCall):
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_found"
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_loaded"
            )
        return cast("ProxonConfigEntry", entry).runtime_data

    async def mark_observation(call: ServiceCall) -> ServiceResponse:
        runtime = runtime_for_call(call)
        try:
            return runtime.capture.mark_observation(
                call.data["label"], call.data["observation"]
            )
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=str(err)
            ) from err

    async def start_event_capture(call: ServiceCall) -> ServiceResponse:
        runtime = runtime_for_call(call)
        if not runtime.connected or not any(
            runtime.get(key) is not None for key in runtime.values
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="event_capture_no_recent_data",
            )
        try:
            return runtime.event_capture.trigger_diagnostic(call.data["label"])
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
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_EVENT_CAPTURE,
        start_event_capture,
        schema=EVENT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
