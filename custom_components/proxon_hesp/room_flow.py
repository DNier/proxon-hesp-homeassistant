"""Optional room CRUD with entity selectors and stable, private room identities."""

import math
import uuid

import voluptuous as vol
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import DOMAIN
from .rooms import CONF_ROOMS, SOURCE_FIELDS, resolve, source_ids


class RoomOptionsMixin:
    """Room flow steps used by the integration's existing options flow."""

    async def async_step_rooms(self, user_input=None):
        return self.async_show_menu(
            step_id="rooms", menu_options=["room_add", "room_edit", "room_remove"]
        )

    def _save_room_options(self, rooms):
        return self.async_create_entry(
            data={
                **self.config_entry.options,
                **self._pending_capture,
                CONF_ROOMS: rooms,
            }
        )

    async def async_step_room_add(self, user_input=None):
        self._room_id = None
        return await self.async_step_room(user_input)

    async def _select_room(self, step, user_input):
        rooms = self.config_entry.options.get(CONF_ROOMS, [])
        if not rooms:
            return self.async_abort(reason="no_rooms")
        if user_input is not None:
            self._room_id = user_input["room"]
            if step == "room_remove":
                return await self.async_step_room_delete()
            return await self.async_step_room()
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(
                {
                    vol.Required("room"): selector.SelectSelector(
                        {
                            "options": [
                                {"value": room["id"], "label": room["name"]}
                                for room in rooms
                            ],
                            "mode": "dropdown",
                        }
                    )
                }
            ),
        )

    async def async_step_room_edit(self, user_input=None):
        return await self._select_room("room_edit", user_input)

    async def async_step_room_remove(self, user_input=None):
        return await self._select_room("room_remove", user_input)

    async def async_step_room_delete(self, user_input=None):
        rooms = self.config_entry.options.get(CONF_ROOMS, [])
        room = next((room for room in rooms if room["id"] == self._room_id), None)
        if room is None:
            return self.async_abort(reason="no_rooms")
        if user_input is not None:
            return self._save_room_options(
                [room for room in rooms if room["id"] != self._room_id]
            )
        return self.async_show_form(
            step_id="room_delete",
            data_schema=vol.Schema({}),
            description_placeholders={"name": room["name"]},
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

    async def async_step_room(self, user_input=None):
        rooms = self.config_entry.options.get(CONF_ROOMS, [])
        existing = next((room for room in rooms if room["id"] == self._room_id), {})
        if self._room_id and not existing:
            return self.async_abort(reason="no_rooms")
        defaults = dict(existing)
        for field in SOURCE_FIELDS:
            if values := defaults.get(field):
                defaults[field] = (
                    [resolve(self.hass, existing, value) or value for value in values]
                    if isinstance(values, list)
                    else (resolve(self.hass, existing, values) or values)
                )
        errors = {}
        if user_input is not None:
            defaults = dict(user_input)
            data = {**user_input, "name": user_input["name"].strip()}
            data["actuators"] = list(dict.fromkeys(data["actuators"]))
            data["power_sensors"] = list(dict.fromkeys(data.get("power_sensors", [])))
            registry = er.async_get(self.hass)
            if not data["name"] or not data["actuators"]:
                errors["base"] = "invalid_room"
            elif not math.isfinite(data["threshold"]):
                errors["threshold"] = "invalid_room"
            elif data.get("area") and not ar.async_get(self.hass).async_get_area(
                data["area"]
            ):
                errors["area"] = "invalid_room"
            elif any(
                registry.async_get(value) is None
                and self.hass.states.get(value) is None
                for value in source_ids(data)
            ):
                errors["base"] = "missing_source"
            elif not self._valid_sources(data):
                errors["base"] = "invalid_room"
            elif any(
                set(data[field])
                & {resolve(self.hass, other, value) for value in other.get(field, [])}
                for other in rooms
                if other["id"] != self._room_id
                for field in ("actuators", "power_sensors")
            ):
                errors["base"] = "source_in_use"
            elif any(
                (registered := registry.async_get(value))
                and registered.platform == DOMAIN
                for value in source_ids(data)
            ):
                errors["base"] = "invalid_room"
            else:
                data["id"] = self._room_id or uuid.uuid4().hex
                data["entity_refs"] = {
                    value: registered.id
                    for value in source_ids(data)
                    if (registered := registry.async_get(value))
                }
                return self._save_room_options(
                    [*[room for room in rooms if room["id"] != self._room_id], data]
                )
        schema = {
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
            vol.Optional("thermostat"): selector.EntitySelector({"domain": "climate"}),
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
            vol.Required("threshold", default=10): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=100000)
            ),
            vol.Required("max_age", default=300): vol.All(
                vol.Coerce(int), vol.Range(min=30, max=86400)
            ),
        }
        return self.async_show_form(
            step_id="room",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), defaults
            ),
        )
