"""Room monitoring: real HA lifecycle, source failures and options CRUD."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import timedelta
from types import MappingProxyType
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.proxon_hesp.const import DOMAIN, PROFILE

ROOM = {
    "id": "room-one",
    "name": "Heating room",
    "actuators": ["switch.heater"],
    "power_sensors": ["sensor.power"],
    "threshold": 10.0,
    "max_age": 300,
}


@pytest.fixture
async def room_entry(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(b"".join(frames.values()))

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
        options={"rooms": [deepcopy(ROOM)]},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


def state(hass, key, room="room-one"):
    platform = "sensor" if key == "power" else "binary_sensor"
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"unit_room_{room}_{key}"
    )
    return hass.states.get(entity_id)


async def test_missing_recovery_power_loss_and_no_control(hass, room_entry):
    assert state(hass, "power").state == "unknown"
    assert state(hass, "heating").state == "unknown"
    assert state(hass, "reachable").state == "off"
    assert state(hass, "actuator_on").state == "unknown"
    with patch("homeassistant.core.ServiceRegistry.async_call") as call:
        hass.states.async_set("switch.heater", "on")
        hass.states.async_set("sensor.power", "0.2", {"unit_of_measurement": "kW"})
        await hass.async_block_till_done()
        assert state(hass, "heating").state == "on"
        assert float(state(hass, "power").state) == 200
        assert state(hass, "reachable").state == "on"
        hass.states.async_set("sensor.power", "unavailable")
        hass.states.async_set("switch.heater", "unavailable")
        await hass.async_block_till_done()
        assert state(hass, "heating").state == "unknown"
        assert state(hass, "power").state == "unknown"
        assert state(hass, "reachable").state == "off"
        hass.states.async_set("switch.heater", "off")
        hass.states.async_set("sensor.power", "0", {"unit_of_measurement": "W"})
        await hass.async_block_till_done()
        assert state(hass, "heating").state == "off"
        assert state(hass, "actuator_on").state == "off"
        call.assert_not_called()


@pytest.mark.parametrize(
    "value,unit",
    [
        ("nan", "W"),
        ("inf", "W"),
        ("-1", "W"),
        ("200", "Wh"),
        ("unknown", "W"),
        ("broken", "W"),
    ],
)
async def test_invalid_power_is_unknown(hass, room_entry, value, unit):
    hass.states.async_set("sensor.power", value, {"unit_of_measurement": unit})
    await hass.async_block_till_done()
    assert state(hass, "heating").state == "unknown"
    assert state(hass, "power").state == "unknown"


async def test_expiry_and_unchanged_report_refresh(hass, room_entry):
    hass.states.async_set("sensor.power", "200", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    future = dt_util.utcnow() + timedelta(seconds=301)
    with patch(
        "custom_components.proxon_hesp.rooms.dt_util.utcnow", return_value=future
    ):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()
        assert state(hass, "heating").state == "unknown"
    hass.states.async_set("sensor.power", "200", {"unit_of_measurement": "W"})
    async_fire_time_changed(hass, future + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert state(hass, "heating").state == "on"


async def update_rooms(hass, entry, rooms):
    desired = {room["id"]: room for room in rooms}
    for sub in list(entry.subentries.values()):
        if sub.data["id"] not in desired:
            hass.config_entries.async_remove_subentry(entry, sub.subentry_id)
        else:
            hass.config_entries.async_update_subentry(
                entry, sub, data=desired.pop(sub.data["id"])
            )
    for room in desired.values():
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType(room),
                subentry_type="room",
                title=room["name"],
                unique_id=room["id"],
            ),
        )
    await hass.async_block_till_done()


async def test_partial_measurements_and_no_power_sensor(hass, room_entry):
    room = {
        **ROOM,
        "actuators": ["switch.heater", "switch.second"],
        "power_sensors": ["sensor.power", "sensor.second"],
    }
    await update_rooms(hass, room_entry, [room])
    hass.states.async_set("switch.heater", "on")
    hass.states.async_set("sensor.power", "200", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert state(hass, "power").state == "unknown"
    assert state(hass, "heating").state == "on"
    assert state(hass, "actuator_on").state == "on"
    assert state(hass, "reachable").state == "off"
    hass.states.async_set("sensor.power", "10", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert state(hass, "heating").state == "unknown"
    hass.states.async_set("sensor.second", "0", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert state(hass, "heating").state == "off"
    await update_rooms(hass, room_entry, [{**room, "power_sensors": []}])
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, "unit_room_room-one_power"
        )
        is None
    )
    assert state(hass, "heating").state == "unknown"


async def test_edit_remove_devices_and_preserve_capture(hass, room_entry):
    registry = er.async_get(hass)
    source = registry.async_get_or_create("switch", "test", "source")
    entity_id = state(hass, "heating").entity_id
    device_id = registry.async_get(entity_id).device_id
    runtime = room_entry.runtime_data
    runtime.capture.start()
    await update_rooms(
        hass,
        room_entry,
        [
            {**ROOM, "name": "Renamed"},
            {
                **ROOM,
                "id": "two",
                "name": "Second room",
                "actuators": [source.entity_id],
                "power_sensors": [],
            },
        ],
    )
    assert state(hass, "heating").entity_id == entity_id
    assert dr.async_get(hass).async_get(device_id).name == "Renamed"
    assert room_entry.runtime_data is runtime
    assert runtime.capture.reason == "recording"
    await update_rooms(hass, room_entry, [])
    assert registry.async_get(entity_id) is None
    assert dr.async_get(hass).async_get(device_id) is None
    assert registry.async_get(source.entity_id) is not None
    assert runtime.capture.reason == "recording"


async def test_registered_source_rename_and_delete(hass, room_entry):
    registry = er.async_get(hass)
    source = registry.async_get_or_create(
        "sensor", "test", "power", suggested_object_id="power"
    )
    room = {
        **ROOM,
        "power_sensors": [source.entity_id],
        "entity_refs": {source.entity_id: source.id},
    }
    await update_rooms(hass, room_entry, [room])
    registry.async_update_entity(source.entity_id, new_entity_id="sensor.renamed_power")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.renamed_power", "200", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert state(hass, "heating").state == "on"
    registry.async_remove("sensor.renamed_power")
    await hass.async_block_till_done()
    assert state(hass, "heating").state == "unknown"


async def subentry_flow(hass, entry, subentry=None):
    context = (
        {"source": "user"}
        if subentry is None
        else {
            "source": "reconfigure",
            "subentry_id": subentry.subentry_id,
        }
    )
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, "room"),
        context=context,
    )


async def test_subentry_add_edit_remove_and_validation(hass, room_entry):
    hass.states.async_set("switch.other", "off")
    hass.states.async_set(
        "sensor.other", "0", {"device_class": "power", "unit_of_measurement": "W"}
    )
    result = await subentry_flow(hass, room_entry)
    data = {
        "name": "Other",
        "actuators": ["switch.other"],
        "power_sensors": ["sensor.other"],
    }
    configure = hass.config_entries.subentries.async_configure
    result = await configure(result["flow_id"], {**data, "name": " "})
    assert result["errors"] == {"base": "invalid_room"}
    result = await configure(
        result["flow_id"], {**data, "actuators": ["switch.missing"]}
    )
    assert result["errors"] == {"base": "missing_source"}
    hass.states.async_set("switch.heater", "off")
    result = await configure(
        result["flow_id"], {**data, "actuators": ["switch.heater"]}
    )
    assert result["errors"] == {"base": "source_in_use"}
    result = await configure(result["flow_id"], data)
    assert result["step_id"] == "references"
    assert len(room_entry.subentries) == 1
    result = await configure(result["flow_id"], {})
    assert result["step_id"] == "advanced"
    result = await configure(result["flow_id"], {"threshold": 15, "max_age": 600})
    await hass.async_block_till_done()
    assert result["type"] == "create_entry"
    sub = next(sub for sub in room_entry.subentries.values() if sub.title == "Other")
    room_id = sub.data["id"]
    entity_id = state(hass, "heating", room_id).entity_id
    registry = er.async_get(hass)
    assert registry.async_get(entity_id).config_subentry_id == sub.subentry_id
    device = dr.async_get(hass).async_get(registry.async_get(entity_id).device_id)
    assert device.config_subentry_id == sub.subentry_id
    options = dict(room_entry.options)
    runtime = room_entry.runtime_data
    runtime.capture.start()
    result = await subentry_flow(hass, room_entry, sub)
    result = await configure(
        result["flow_id"], {**data, "name": "New name", "power_sensors": []}
    )
    result = await configure(result["flow_id"], {})
    result = await configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert sub.title == "New name"
    assert state(hass, "heating", room_id).entity_id == entity_id
    assert state(hass, "heating", room_id).state == "unknown"
    assert sub.data["threshold"] == 15
    assert sub.data["max_age"] == 600
    assert room_entry.options == options
    assert runtime.capture.reason == "recording"
    hass.config_entries.async_remove_subentry(room_entry, sub.subentry_id)
    await hass.async_block_till_done()
    assert len(room_entry.subentries) == 1
    assert registry.async_get(entity_id) is None
    assert dr.async_get(hass).async_get(device.id) is None
    assert hass.states.get("switch.other").state == "off"
    assert runtime.capture.reason == "recording"


async def test_reload_preserves_identity_and_area(hass, room_entry):
    from homeassistant.helpers import area_registry as ar

    area = ar.async_get(hass).async_create("Study")
    await update_rooms(hass, room_entry, [{**ROOM, "area": area.id}])
    registry = er.async_get(hass)
    entity_id = state(hass, "heating").entity_id
    device_id = registry.async_get(entity_id).device_id
    assert dr.async_get(hass).async_get(device_id).area_id == area.id
    hass.states.async_set("sensor.power", "200", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    # A fresh receiver is necessary on reload, as each stream has its own frames.
    from custom_components.proxon_hesp.coordinator import ProxonRuntime

    async def start(runtime, entry):
        runtime.ready.set()

    with patch.object(ProxonRuntime, "start", start):
        assert await hass.config_entries.async_reload(room_entry.entry_id)
        await hass.async_block_till_done()
    assert state(hass, "heating").entity_id == entity_id
    assert state(hass, "heating").state == "on"
    assert registry.async_get(entity_id).device_id == device_id
    assert dr.async_get(hass).async_get(device_id).area_id == area.id


async def test_restored_placeholder_is_not_a_measurement(hass, room_entry):
    hass.states.async_set(
        "sensor.power", "200", {"unit_of_measurement": "W", "restored": True}
    )
    await hass.async_block_till_done()
    assert state(hass, "power").state == "unknown"
    assert state(hass, "heating").state == "unknown"


async def test_disabled_room_entity_removal(hass, room_entry):
    from custom_components.proxon_hesp.coordinator import ProxonRuntime

    registry = er.async_get(hass)
    entity_id = state(hass, "heating").entity_id
    registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    await hass.async_block_till_done()

    async def start(runtime, entry):
        runtime.ready.set()

    with patch.object(ProxonRuntime, "start", start):
        await hass.config_entries.async_reload(room_entry.entry_id)
        await hass.async_block_till_done()
    assert hass.states.get(entity_id) is None
    await update_rooms(hass, room_entry, [])
    assert registry.async_get(entity_id) is None


async def test_cancel_room_flow_and_capture_options_are_independent(hass, room_entry):
    result = await subentry_flow(hass, room_entry)
    hass.config_entries.subentries.async_abort(result["flow_id"])
    assert len(room_entry.subentries) == 1
    options = await hass.config_entries.options.async_init(room_entry.entry_id)
    assert "manage_rooms" not in options["data_schema"]({})
    await hass.config_entries.options.async_configure(
        options["flow_id"],
        {
            "capture_duration": 600,
            "event_capture_enabled": True,
        },
    )
    await hass.async_block_till_done()
    assert len(room_entry.subentries) == 1
    assert room_entry.options["capture_duration"] == 600


async def test_invalid_measurement_type_rejected(hass, room_entry):
    hass.states.async_set("switch.other", "off")
    hass.states.async_set(
        "sensor.energy", "200", {"device_class": "energy", "unit_of_measurement": "kWh"}
    )
    result = await subentry_flow(hass, room_entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Another room",
            "actuators": ["switch.other"],
            "power_sensors": ["sensor.energy"],
        },
    )
    assert result["errors"] == {"base": "invalid_room"}


async def test_area_override_survives_capture_option_change(hass, room_entry):
    from homeassistant.helpers import area_registry as ar

    area = ar.async_get(hass).async_create("Custom area")
    registry = er.async_get(hass)
    device_id = registry.async_get(state(hass, "heating").entity_id).device_id
    devices = dr.async_get(hass)
    devices.async_update_device(device_id, area_id=area.id)
    hass.config_entries.async_update_entry(
        room_entry,
        options={
            **room_entry.options,
            "capture_duration": 600,
        },
    )
    await hass.async_block_till_done()
    assert devices.async_get(device_id).area_id == area.id


async def test_room_cleanup_preserves_existing_controller_room_temperature(
    hass, room_entry
):
    """The legacy room_temperature ID shares the prefix, but not the room device."""
    from custom_components.proxon_hesp.rooms import sync_room_devices

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "unit_room_temperature")
    original = registry.async_get(entity_id)
    registry.async_update_entity(entity_id, name="Custom temperature label")
    sync_room_devices(hass, room_entry)
    assert registry.async_get(entity_id).id == original.id
    assert registry.async_get(entity_id).name == "Custom temperature label"
    await update_rooms(hass, room_entry, [])
    assert registry.async_get(entity_id).id == original.id


async def test_new_room_area_applied_when_entities_register_device_first(
    hass, room_entry
):
    """Entity platform registration may create the device before options sync."""
    from homeassistant.helpers import area_registry as ar

    area = ar.async_get(hass).async_create("New room")
    new_room = {**ROOM, "id": "new-room", "name": "New room", "area": area.id}
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=room_entry.entry_id,
        identifiers={(DOMAIN, "unit_room_new-room")},
        name="New room",
    )
    await update_rooms(hass, room_entry, [ROOM, new_room])
    assert dr.async_get(hass).async_get(device.id).area_id == area.id


async def test_existing_unassigned_room_recovers_saved_area(hass, room_entry):
    from homeassistant.helpers import area_registry as ar

    from custom_components.proxon_hesp.rooms import sync_room_devices

    area = ar.async_get(hass).async_create("Saved room area")
    room = {**ROOM, "area": area.id}
    await update_rooms(hass, room_entry, [room])
    device_id = er.async_get(hass).async_get(state(hass, "heating").entity_id).device_id
    devices = dr.async_get(hass)
    devices.async_update_device(device_id, area_id=None)
    sync_room_devices(hass, room_entry)
    assert devices.async_get(device_id).area_id == area.id
    manual = ar.async_get(hass).async_create("Manual assignment")
    devices.async_update_device(device_id, area_id=manual.id)
    sync_room_devices(hass, room_entry)
    assert devices.async_get(device_id).area_id == manual.id


async def test_beta_migration_preserves_registry_identity_and_configuration(hass):
    """Migrate already-created beta devices, including disabled entity settings."""
    from homeassistant.helpers import area_registry as ar

    from custom_components.proxon_hesp import async_migrate_entry
    from custom_components.proxon_hesp.coordinator import ProxonRuntime

    area = ar.async_get(hass).async_create("Room area")
    room = {**ROOM, "area": area.id, "threshold": 17, "max_age": 720}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="unit",
        version=1,
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
        options={
            "rooms": [room],
            "capture_duration": 600,
            "event_capture_enabled": True,
        },
    )
    entry.add_to_hass(hass)
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "unit_room_room-one")},
        name="Heating room",
    )
    devices.async_update_device(device.id, area_id=area.id, name_by_user="My room")
    entities = er.async_get(hass)
    entity = entities.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "unit_room_room-one_heating",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id="existing_heating",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    entities.async_update_entity(entity.entity_id, name="My heating", icon="mdi:fire")

    async def start(runtime, entry):
        runtime.ready.set()

    with patch.object(ProxonRuntime, "start", start):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.version == 2
        assert "rooms" not in entry.options
        assert entry.options == {"capture_duration": 600, "event_capture_enabled": True}
        assert len(entry.subentries) == 1
        sub = next(iter(entry.subentries.values()))
        assert dict(sub.data) == room
        current = entities.async_get(entity.entity_id)
        assert current.id == entity.id
        assert current.device_id == device.id
        assert current.config_subentry_id == sub.subentry_id
        assert current.name == "My heating"
        assert current.disabled_by == er.RegistryEntryDisabler.USER
        assert current.icon == "mdi:fire"
        assert devices.async_get(device.id).config_subentry_id == sub.subentry_id
        assert devices.async_get(device.id).area_id == area.id
        assert devices.async_get(device.id).name_by_user == "My room"
        assert await async_migrate_entry(hass, entry)
        assert len(entry.subentries) == 1
        await hass.config_entries.async_unload(entry.entry_id)


async def test_subentry_reconfigure_cancel_and_clear_references(hass, room_entry):
    sub = next(iter(room_entry.subentries.values()))
    hass.states.async_set("switch.heater", "off")
    hass.states.async_set(
        "sensor.power", "0", {"device_class": "power", "unit_of_measurement": "W"}
    )
    hass.states.async_set("climate.other", "heat")
    original = dict(sub.data)
    flow = await subentry_flow(hass, room_entry, sub)
    configure = hass.config_entries.subentries.async_configure
    flow = await configure(
        flow["flow_id"], {"name": "Changed", "actuators": ["switch.heater"]}
    )
    flow = await configure(flow["flow_id"], {"thermostat": "climate.other"})
    assert dict(sub.data) == original
    hass.config_entries.subentries.async_abort(flow["flow_id"])
    assert dict(sub.data) == original
    hass.config_entries.async_update_subentry(
        room_entry, sub, data={**original, "thermostat": "climate.other"}
    )
    await hass.async_block_till_done()
    flow = await subentry_flow(hass, room_entry, sub)
    flow = await configure(
        flow["flow_id"], {"name": "Changed", "actuators": ["switch.heater"]}
    )
    flow = await configure(flow["flow_id"], {})
    await configure(flow["flow_id"], {})
    await hass.async_block_till_done()
    assert "thermostat" not in sub.data
    assert sub.data["power_sensors"] == []
