"""Native heating-room subentries with staged, atomic configuration."""

import math
import uuid

import voluptuous as vol
from homeassistant.config_entries import ConfigSubentryFlow
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import DOMAIN
from .rooms import SOURCE_FIELDS, configured_rooms, resolve, source_ids

BASIC = ("name", "area", "actuators", "power_sensors")
REFERENCES = ("thermostat", "temperature", "humidity")


class RoomSubentryFlow(ConfigSubentryFlow):
    """Collect all steps before creating or changing a room."""

    def __init__(self):
        self._room = None
        self._subentry = None

    async def async_step_reconfigure(self, user_input=None):
        self._subentry = self._get_reconfigure_subentry()
        return await self.async_step_user(user_input)

    def _initialize(self):
        if self._room is not None:
            return
        original = dict(self._subentry.data) if self._subentry else {}
        self._room = {
            "id": uuid.uuid4().hex,
            "threshold": 10.0,
            "max_age": 300,
            **original,
        }
        for field in SOURCE_FIELDS:
            if values := original.get(field):
                self._room[field] = (
                    [resolve(self.hass, original, value) or value for value in values]
                    if isinstance(values, list)
                    else (resolve(self.hass, original, values) or values)
                )

    def _validate(self, data):
        registry = er.async_get(self.hass)
        if not data.get("name", "").strip() or not data.get("actuators"):
            return "invalid_room"
        if data.get("area") and not ar.async_get(self.hass).async_get_area(
            data["area"]
        ):
            return "invalid_room"
        if any(
            registry.async_get(value) is None and self.hass.states.get(value) is None
            for value in source_ids(data)
        ):
            return "missing_source"
        if not self._valid_sources(data):
            return "invalid_room"
        if any(
            set(data.get(field, []))
            & {resolve(self.hass, other, value) for value in other.get(field, [])}
            for other in configured_rooms(self._get_entry())
            if other["id"] != data["id"]
            for field in ("actuators", "power_sensors")
        ):
            return "source_in_use"
        if any(
            (registered := registry.async_get(value)) and registered.platform == DOMAIN
            for value in source_ids(data)
        ):
            return "invalid_room"
        return None

    def _form(self, step, schema, errors=None):
        return self.async_show_form(
            step_id=step,
            errors=errors or {},
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), self._room
            ),
        )

    async def async_step_user(self, user_input=None):
        self._initialize()
        errors = {}
        if user_input is not None:
            for field in BASIC:
                self._room.pop(field, None)
            self._room.update(user_input)
            self._room["name"] = self._room["name"].strip()
            for field in ("actuators", "power_sensors"):
                self._room[field] = list(dict.fromkeys(self._room.get(field, [])))
            # References may be repaired in the next step; validate the basics first.
            basic = {
                key: value for key, value in self._room.items() if key not in REFERENCES
            }
            if error := self._validate(basic):
                errors["base"] = error
            else:
                return await self.async_step_references()
        return self._form(
            "user",
            {
                vol.Required("name"): str,
                vol.Optional("area"): selector.AreaSelector(),
                vol.Required("actuators"): selector.EntitySelector(
                    {
                        "domain": "switch",
                        "multiple": True,
                    }
                ),
                vol.Optional("power_sensors"): selector.EntitySelector(
                    {
                        "domain": "sensor",
                        "device_class": "power",
                        "multiple": True,
                    }
                ),
            },
            errors,
        )

    async def async_step_references(self, user_input=None):
        errors = {}
        if user_input is not None:
            for field in REFERENCES:
                self._room.pop(field, None)
            self._room.update(user_input)
            if error := self._validate(self._room):
                errors["base"] = error
            else:
                return await self.async_step_advanced()
        return self._form(
            "references",
            {
                vol.Optional("thermostat"): selector.EntitySelector(
                    {"domain": "climate"}
                ),
                vol.Optional("temperature"): selector.EntitySelector(
                    {
                        "domain": "sensor",
                        "device_class": "temperature",
                    }
                ),
                vol.Optional("humidity"): selector.EntitySelector(
                    {
                        "domain": "sensor",
                        "device_class": "humidity",
                    }
                ),
            },
            errors,
        )

    async def async_step_advanced(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._room.update(user_input)
            if not math.isfinite(self._room["threshold"]):
                errors["base"] = "invalid_room"
            elif error := self._validate(self._room):
                # Recheck for removed sources or conflicting rooms created meanwhile.
                return self.async_abort(reason=error)
            else:
                registry = er.async_get(self.hass)
                self._room["entity_refs"] = {
                    value: registered.id
                    for value in source_ids(self._room)
                    if (registered := registry.async_get(value))
                }
                if self._subentry:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        self._get_reconfigure_subentry(),
                        title=self._room["name"],
                        data=dict(self._room),
                    )
                return self.async_create_entry(
                    title=self._room["name"],
                    data=dict(self._room),
                    unique_id=self._room["id"],
                )
        return self._form(
            "advanced",
            {
                vol.Required("threshold", default=self._room["threshold"]): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=100000)
                ),
                vol.Required("max_age", default=self._room["max_age"]): vol.All(
                    int, vol.Range(min=30, max=86400)
                ),
            },
            errors,
        )

    def _valid_sources(self, data):
        """Selectors filter the UI; also validate the submitted source types."""
        for field in SOURCE_FIELDS:
            values = data.get(field, [])
            if isinstance(values, str):
                values = [values]
            domain = {"actuators": "switch", "thermostat": "climate"}.get(
                field, "sensor"
            )
            device_class = {
                "power_sensors": "power",
                "temperature": "temperature",
                "humidity": "humidity",
            }.get(field)
            for value in values:
                if value.split(".", 1)[0] != domain:
                    return False
                state = self.hass.states.get(value)
                if state and device_class:
                    actual = state.attributes.get("device_class")
                    if actual is not None and actual != device_class:
                        return False
                    if (
                        field == "power_sensors"
                        and (unit := state.attributes.get("unit_of_measurement"))
                        is not None
                        and unit not in ("W", "kW")
                    ):
                        return False
        return True
