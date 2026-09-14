"""Admin-only, two-step experimental actions; no automatic writes."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN
from .write_test import ExperimentRejected

PREPARE = "prepare_target_temperature_test"
SEND = "send_target_temperature_test"


def register_services(hass: HomeAssistant) -> None:
    async def handle(call: ServiceCall) -> dict | None:
        # Require a directly authenticated user as well as the admin-service
        # permission check. Unattended scripts must not initiate this experiment.
        if call.context.user_id is None:
            raise ServiceValidationError("Run this experiment as an administrator.")
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state != ConfigEntryState.LOADED
        ):
            raise ServiceValidationError(
                "Select a loaded PROXON HESP integration entry."
            )
        test = entry.runtime_data.temperature_test
        try:
            if call.service == PREPARE:
                if not call.return_response:
                    raise ServiceValidationError(
                        "Request response data to receive the confirmation token."
                    )
                return test.prepare(
                    call.data["expected_temperature"], call.data["delta"]
                )
            result = await test.send(call.data["confirmation_token"])
        except ExperimentRejected as err:
            raise ServiceValidationError(str(err)) from err
        except (OSError, TimeoutError) as err:
            raise ServiceValidationError(
                "Delivery is unknown. Attempt consumed; do not retry. Save diagnostics."
            ) from err
        return result if call.return_response else None

    for name, fields in (
        (
            PREPARE,
            {
                vol.Required("expected_temperature"): vol.Coerce(float),
                vol.Required("delta"): vol.In([-0.5, 0.5]),
            },
        ),
        (SEND, {vol.Required("confirmation_token"): cv.string}),
    ):
        async_register_admin_service(
            hass,
            DOMAIN,
            name,
            handle,
            schema=vol.Schema({vol.Required("config_entry_id"): cv.string, **fields}),
            supports_response=SupportsResponse.OPTIONAL,
        )
