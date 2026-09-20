"""UI setup with a receive-only protocol probe and stable local identity."""

import uuid

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .capture import DURATION, MAX_DURATION, MIN_DURATION, validate_duration
from .const import (
    CONF_CAPTURE_DURATION,
    CONF_EVENT_CAPTURE,
    CONF_PROFILE,
    DEFAULT_PORT,
    DOMAIN,
    PROBE_TIMEOUT,
    PROFILE,
)
from .hesp.transport import NoSupportedData, probe


class ProxonConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> ProxonOptionsFlow:
        return ProxonOptionsFlow()

    def _schema(self, defaults: dict) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
                ): cv.port,
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "PROXON")): str,
                vol.Required(CONF_PROFILE, default=PROFILE): vol.In([PROFILE]),
            }
        )

    async def _step(self, step: str, user_input: dict | None) -> ConfigFlowResult:
        errors = {}
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        defaults = {**entry.data, CONF_NAME: entry.title} if entry else {}
        if user_input is not None:
            data = dict(user_input)
            data[CONF_HOST] = data[CONF_HOST].strip().lower()
            data[CONF_NAME] = data[CONF_NAME].strip()
            defaults = data
            if not data[CONF_HOST] or not data[CONF_NAME]:
                errors["base"] = "invalid_input"
            elif any(
                other.entry_id != (entry.entry_id if entry else None)
                and other.data.get(CONF_HOST) == data[CONF_HOST]
                and other.data.get(CONF_PORT) == data[CONF_PORT]
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            else:
                try:
                    # A one-client gateway is already owned by the loaded entry.
                    same_endpoint = entry and all(
                        data[key] == entry.data[key] for key in (CONF_HOST, CONF_PORT)
                    )
                    if not same_endpoint:
                        await probe(data[CONF_HOST], data[CONF_PORT], PROBE_TIMEOUT)
                except NoSupportedData:
                    errors["base"] = "no_supported_data"
                except OSError, TimeoutError:
                    errors["base"] = "cannot_connect"
                else:
                    title = data.pop(CONF_NAME)
                    if entry:
                        return self.async_update_reload_and_abort(
                            entry, data_updates=data, title=title
                        )
                    await self.async_set_unique_id(uuid.uuid4().hex)
                    return self.async_create_entry(title=title, data=data)
        return self.async_show_form(
            step_id=step, data_schema=self._schema(defaults), errors=errors
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        return await self._step("user", user_input)

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        return await self._step("reconfigure", user_input)


class ProxonOptionsFlow(OptionsFlow):
    """Configure recording limits without touching the gateway connection."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            try:
                duration = validate_duration(user_input[CONF_CAPTURE_DURATION])
            except ValueError, KeyError:
                errors[CONF_CAPTURE_DURATION] = "invalid_duration"
            else:
                return self.async_create_entry(
                    data={
                        **self.config_entry.options,
                        CONF_CAPTURE_DURATION: duration,
                        CONF_EVENT_CAPTURE: user_input.get(
                            CONF_EVENT_CAPTURE,
                            self.config_entry.options.get(CONF_EVENT_CAPTURE, False),
                        ),
                    }
                )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CAPTURE_DURATION,
                        default=self.config_entry.options.get(
                            CONF_CAPTURE_DURATION, DURATION
                        ),
                    ): vol.All(int, vol.Range(min=MIN_DURATION, max=MAX_DURATION)),
                    vol.Required(
                        CONF_EVENT_CAPTURE,
                        default=self.config_entry.options.get(
                            CONF_EVENT_CAPTURE, False
                        ),
                    ): bool,
                }
            ),
            errors=errors,
        )
