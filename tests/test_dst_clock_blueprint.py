"""Exercise the opt-in DST blueprint with Home Assistant and a fake button."""

from datetime import datetime, timedelta
from pathlib import Path
from shutil import copyfile

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.proxon_hesp.const import DOMAIN

BLUEPRINT = "proxon_hesp/dst_clock_sync.yaml"
SOURCE = Path(__file__).resolve().parents[1] / "blueprints" / "automation" / BLUEPRINT
AUTOMATION = "automation.dst_clock_sync_test"
BERLIN_SPRING = "2027-03-28T02:15:00+00:00"
BERLIN_SPRING_CLOCK = "2027-03-28T03:15"


@pytest.fixture
def hass_config_dir(tmp_path):
    destination = tmp_path / "blueprints" / "automation" / BLUEPRINT
    destination.parent.mkdir(parents=True)
    copyfile(SOURCE, destination)
    return str(tmp_path)


@pytest.fixture(autouse=True)
async def detach_time_trigger(hass):
    yield
    if hass.states.is_state(AUTOMATION, "on"):
        await hass.services.async_call(
            "automation", "turn_off", {"entity_id": AUTOMATION}, blocking=True
        )


@pytest.fixture
def clock_entities(hass):
    config = MockConfigEntry(domain=DOMAIN, unique_id="proxon-test")
    config.add_to_hass(hass)
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=config.entry_id, identifiers={(DOMAIN, "proxon-test")}
    )
    entities = er.async_get(hass)
    calendar = entities.async_get_or_create(
        "sensor",
        DOMAIN,
        "proxon-test_device_datetime",
        config_entry=config,
        device_id=device.id,
    )
    button = entities.async_get_or_create(
        "button",
        DOMAIN,
        "proxon-test_clock_sync",
        config_entry=config,
        device_id=device.id,
    )
    return calendar.entity_id, button.entity_id


async def setup_automation(
    hass,
    freezer,
    clock_entities,
    *,
    timezone,
    start,
    calendar_value,
    button_state="unknown",
    button_status="idle",
    enabled=True,
    failure=None,
):
    freezer.move_to(start)
    await hass.config.async_set_time_zone(timezone)
    calendar, button = clock_entities
    hass.states.async_set(calendar, calendar_value)
    hass.states.async_set(button, button_state, {"status": button_status})
    calls = async_mock_service(hass, "button", "press", raise_exception=failure)
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "alias": "DST clock sync test",
                    "id": "dst_clock_sync_test",
                    "use_blueprint": {
                        "path": BLUEPRINT,
                        "input": {"clock_sensor": calendar, "sync_button": button},
                    },
                }
            ]
        },
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        "automation",
        "turn_on" if enabled else "turn_off",
        {"entity_id": AUTOMATION},
        blocking=True,
    )
    await hass.async_block_till_done()
    return calls


async def fire_time(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, instant)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("timezone", "instant", "calendar_value"),
    [
        ("Europe/Berlin", BERLIN_SPRING, "2027-03-28T03:14"),
        ("Europe/Berlin", "2027-10-31T03:15:00+00:00", "2027-10-31T05:15"),
        ("Australia/Lord_Howe", "2027-10-02T17:15:00+00:00", "2027-10-03T03:45"),
        ("Australia/Lord_Howe", "2027-04-03T17:45:00+00:00", "2027-04-04T04:45"),
    ],
)
async def test_scheduled_offset_change_presses_button_once(
    hass, freezer, clock_entities, timezone, instant, calendar_value
):
    due = datetime.fromisoformat(instant)
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone=timezone,
        start=due - timedelta(seconds=1),
        calendar_value=calendar_value,
    )
    assert hass.states.is_state(AUTOMATION, "on")
    assert not calls
    await fire_time(hass, freezer, due)
    assert len(calls) == 1
    assert calls[0].data["entity_id"] == [clock_entities[1]]
    await fire_time(hass, freezer, due + timedelta(minutes=15))
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("timezone", "instant", "calendar_value", "button_state", "button_status"),
    [
        ("UTC", "2027-03-28T04:15:00+00:00", BERLIN_SPRING_CLOCK, "unknown", "idle"),
        (
            "Europe/Berlin",
            "2027-03-29T02:15:00+00:00",
            "2027-03-29T03:15",
            "unknown",
            "idle",
        ),
        ("Europe/Berlin", BERLIN_SPRING, "2027-03-28T04:15", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, "2027-03-28T05:15", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, "2027-03-28T03:10", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, "unknown", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, "unavailable", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, "invalid", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, "2027-03-28T03:15+01:00", "unknown", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, BERLIN_SPRING_CLOCK, "unavailable", "idle"),
        ("Europe/Berlin", BERLIN_SPRING, BERLIN_SPRING_CLOCK, "unknown", "other"),
    ],
)
async def test_scheduled_check_skips_ineligible_clock_state(
    hass,
    freezer,
    clock_entities,
    timezone,
    instant,
    calendar_value,
    button_state,
    button_status,
):
    due = datetime.fromisoformat(instant)
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone=timezone,
        start=due - timedelta(seconds=1),
        calendar_value=calendar_value,
        button_state=button_state,
        button_status=button_status,
    )
    await fire_time(hass, freezer, due)
    assert not calls


async def test_scheduled_check_skips_button_on_other_device(
    hass, freezer, clock_entities
):
    entries = er.async_get(hass)
    button = entries.async_get(clock_entities[1])
    other = dr.async_get(hass).async_get_or_create(
        config_entry_id=button.config_entry_id, identifiers={(DOMAIN, "other-proxon")}
    )
    entries.async_update_entity(button.entity_id, device_id=other.id)
    due = datetime.fromisoformat(BERLIN_SPRING)
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone="Europe/Berlin",
        start=due - timedelta(seconds=1),
        calendar_value=BERLIN_SPRING_CLOCK,
    )
    await fire_time(hass, freezer, due)
    assert not calls


async def test_run_actions_does_not_press_button_at_the_scheduled_time(
    hass, freezer, clock_entities
):
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone="Europe/Berlin",
        start=datetime.fromisoformat(BERLIN_SPRING),
        calendar_value=BERLIN_SPRING_CLOCK,
    )
    await hass.services.async_call(
        "automation", "trigger", {"entity_id": AUTOMATION}, blocking=True
    )
    assert not calls


async def test_disabled_automation_does_not_press_button(hass, freezer, clock_entities):
    due = datetime.fromisoformat(BERLIN_SPRING)
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone="Europe/Berlin",
        start=due - timedelta(seconds=1),
        calendar_value=BERLIN_SPRING_CLOCK,
        enabled=False,
    )
    assert hass.states.is_state(AUTOMATION, "off")
    await fire_time(hass, freezer, due)
    assert not calls


async def test_starting_after_scheduled_check_does_not_catch_up(
    hass, freezer, clock_entities
):
    due = datetime.fromisoformat(BERLIN_SPRING)
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone="Europe/Berlin",
        start=due + timedelta(minutes=1),
        calendar_value="2027-03-28T03:16",
    )
    assert hass.states.is_state(AUTOMATION, "on")
    await fire_time(hass, freezer, due + timedelta(minutes=2))
    assert not calls


async def test_button_error_does_not_retry(hass, freezer, clock_entities):
    due = datetime.fromisoformat(BERLIN_SPRING)
    calls = await setup_automation(
        hass,
        freezer,
        clock_entities,
        timezone="Europe/Berlin",
        start=due - timedelta(seconds=1),
        calendar_value=BERLIN_SPRING_CLOCK,
        failure=HomeAssistantError("Device time update unconfirmed"),
    )
    await fire_time(hass, freezer, due)
    await fire_time(hass, freezer, due + timedelta(minutes=15))
    assert len(calls) == 1
