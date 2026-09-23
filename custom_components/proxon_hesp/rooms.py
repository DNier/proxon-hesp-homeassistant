"""Read-only, manufacturer-independent room monitoring of existing HA entities."""

import math
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN

CONF_ROOMS = "rooms"
SOURCE_FIELDS = ("actuators", "power_sensors", "thermostat", "temperature", "humidity")


def source_ids(room):
    """Enumerate configured external entities without duplicates."""
    return list(
        dict.fromkeys(
            entity_id
            for field in SOURCE_FIELDS
            for entity_id in (
                room.get(field, [])
                if field in ("actuators", "power_sensors")
                else [room[field]]
                if room.get(field)
                else []
            )
        )
    )


def resolve(hass, room, entity_id):
    """Follow registry-backed source renames, never reuse a deleted identity."""
    if registry_id := room.get("entity_refs", {}).get(entity_id):
        registered = er.async_get(hass).async_get(registry_id)
        return registered.entity_id if registered else None
    return entity_id


def room_device_id(entry, room):
    return f"{entry.unique_id}_room_{room['id']}"


def room_keys(room, platform):
    if platform == "sensor":
        return ["power"] if room.get("power_sensors") else []
    return ["reachable", "actuator_on", "heating"]


async def async_setup_rooms(hass, entry, add_entities, platform):
    """Reconcile only this platform's room entities without restarting reception."""
    entities = {}

    async def update():
        rooms = entry.options.get(CONF_ROOMS, [])
        desired = {
            (room["id"], key): room
            for room in rooms
            for key in room_keys(room, platform)
        }
        registry = er.async_get(hass)
        for identity in entities.keys() - desired.keys():
            entity = entities.pop(identity)
            if entity.entity_id and entity.hass:
                await entity.async_remove()
            registered_id = registry.async_get_entity_id(
                platform, DOMAIN, entity.unique_id
            )
            if registered_id:
                registry.async_remove(registered_id)
        added = []
        for identity, room in desired.items():
            if identity in entities:
                entity = entities[identity]
                entity.room = room
                if entity.hass:
                    entity.bind_sources()
                    entity.async_write_ha_state()
            else:
                cls = RoomPowerSensor if platform == "sensor" else RoomBinarySensor
                entity = entities[identity] = cls(entry, room, identity[1])
                added.append(entity)
        if added:
            add_entities(added)

    entry.runtime_data.room_updates.append(update)
    entry.async_on_unload(lambda: entry.runtime_data.room_updates.remove(update))
    await update()


def sync_room_devices(hass, entry, previous=None):
    """Update virtual devices and remove only obsolete integration-owned records."""
    registry = dr.async_get(hass)
    rooms = entry.options.get(CONF_ROOMS, [])
    desired = {room_device_id(entry, room) for room in rooms}
    entity_ids = {
        f"{room_device_id(entry, room)}_{key}"
        for room in rooms
        for platform in ("sensor", "binary_sensor")
        for key in room_keys(room, platform)
    }
    room_devices = {
        device.id
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id)
        if any(
            domain == DOMAIN and value.startswith(f"{entry.unique_id}_room_")
            for domain, value in device.identifiers
        )
    }
    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if (
            entity.platform == DOMAIN
            and entity.device_id in room_devices
            and entity.unique_id not in entity_ids
        ):
            entity_registry.async_remove(entity.entity_id)
    previous_by_id = {room["id"]: room for room in previous or []}
    existing_ids = {
        value
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id)
        for domain, value in device.identifiers
        if domain == DOMAIN
    }
    prefix = f"{entry.unique_id}_room_"
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if any(
            domain == DOMAIN and value.startswith(prefix) and value not in desired
            for domain, value in device.identifiers
        ):
            registry.async_remove_device(device.id)
    for room in rooms:
        device = registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, room_device_id(entry, room))},
            name=room["name"],
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        # Explicit room configuration owns area assignment; source devices stay put.
        area_id = room.get("area")
        if area_id and not ar.async_get(hass).async_get_area(area_id):
            area_id = None
        old = previous_by_id.get(room["id"], room)
        if room_device_id(entry, room) not in existing_ids or old.get(
            "area"
        ) != room.get("area"):
            registry.async_update_device(device.id, area_id=area_id)


class RoomEntity(Entity):
    """Observe external states; no services or bus writes are used."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry, room, key):
        self.room = room
        self.key = key
        self._unsubscribe_sources = None
        self._attr_unique_id = f"{room_device_id(entry, room)}_{key}"
        self._attr_translation_key = f"room_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room_device_id(entry, room))},
            name=room["name"],
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self):
        self.bind_sources()
        self.async_on_remove(self.unbind_sources)
        self.async_on_remove(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self.registry_changed
            )
        )
        self.async_on_remove(
            async_track_time_interval(self.hass, self.refresh, timedelta(seconds=30))
        )

    @callback
    def registry_changed(self, event):
        self.bind_sources()
        self.async_write_ha_state()

    @callback
    def unbind_sources(self):
        if self._unsubscribe_sources:
            self._unsubscribe_sources()
            self._unsubscribe_sources = None

    @callback
    def bind_sources(self):
        self.unbind_sources()
        ids = [resolve(self.hass, self.room, value) for value in source_ids(self.room)]
        if ids := [value for value in ids if value]:
            self._unsubscribe_sources = async_track_state_change_event(
                self.hass, ids, self.refresh
            )

    @callback
    def refresh(self, _event):
        self.async_write_ha_state()

    def source_state(self, entity_id):
        resolved = resolve(self.hass, self.room, entity_id)
        state = self.hass.states.get(resolved) if resolved else None
        if (
            state is None
            or state.state in ("unknown", "unavailable")
            or state.attributes.get("restored")
        ):
            return None
        return state

    def power_values(self):
        values = []
        for entity_id in self.room.get("power_sensors", []):
            state = self.source_state(entity_id)
            value = None
            if (
                state
                and (dt_util.utcnow() - state.last_reported).total_seconds()
                <= self.room["max_age"]
            ):
                try:
                    number = float(state.state)
                    unit = state.attributes.get("unit_of_measurement")
                    if unit in ("W", "kW") and math.isfinite(number) and number >= 0:
                        value = number * (1000 if unit == "kW" else 1)
                except ValueError:
                    pass
            values.append(value)
        return values

    @property
    def extra_state_attributes(self):
        return {
            "sources": {
                field: [resolve(self.hass, self.room, value) for value in values]
                if isinstance(values, list)
                else resolve(self.hass, self.room, values)
                for field in SOURCE_FIELDS
                if (values := self.room.get(field))
            },
            "power_threshold_w": self.room["threshold"],
            "power_max_age_seconds": self.room["max_age"],
        }


class RoomPowerSensor(RoomEntity, SensorEntity):
    _attr_device_class = "power"
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = "measurement"

    @property
    def native_value(self):
        values = self.power_values()
        return sum(values) if values and None not in values else None


class RoomBinarySensor(RoomEntity, BinarySensorEntity):
    @property
    def device_class(self):
        return {"reachable": "connectivity", "heating": "heat"}.get(self.key)

    @property
    def is_on(self):
        if self.key == "heating":
            values = self.power_values()
            # A partial positive sum proves consumption, not a complete total.
            if (
                sum(value for value in values if value is not None)
                > self.room["threshold"]
            ):
                return True
            return False if values and None not in values else None
        states = [self.source_state(value) for value in self.room["actuators"]]
        valid = [state and state.state in ("on", "off") for state in states]
        if self.key == "reachable":
            return all(valid)
        if any(state and state.state == "on" for state in states):
            return True
        return False if all(valid) else None
