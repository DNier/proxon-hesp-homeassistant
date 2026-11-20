"""Passive service settings: recorded vectors and conservative channel guards."""

import asyncio
import json
import struct
import time
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.coordinator import ProxonRuntime
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from custom_components.proxon_hesp.sensor import DESCRIPTIONS

CURVES = json.loads(
    (Path(__file__).parent / "fixtures/fan_curve_replies.json").read_text()
)
UNITS = {
    "cooling_threshold": "°C",
    "heat_pump_start_threshold": "K",
    "heat_pump_continuous_run_threshold": "°C",
    "max_heating_output": "%",
    "max_cooling_output": "%",
    **{
        f"fan_{direction}_stage_{stage}": "%"
        for direction in ("supply", "extract")
        for stage in range(1, 5)
    },
}


def frame(dp, payload, identity=b"\x22\x40\x00"):
    body = (
        identity
        + dp.to_bytes(2, "little")
        + b"\0\0"
        + bytes([len(payload) * 2])
        + payload
    )
    return body + checksum(body).to_bytes(2, "little")


SETTINGS_FRAMES = (
    bytes.fromhex(CURVES["00d2"])
    + bytes.fromhex(CURVES["00d3"])
    + frame(0x110, struct.pack("<f", 3))
    + frame(0x115, struct.pack("<f", 0.399993896))
    + frame(0x11C, struct.pack("<f", 2))
    + frame(0x116, struct.pack("<2H", 100, 90))
)


@pytest.mark.parametrize(
    "dp,direction,values",
    [("00d2", "supply", [31, 50, 70, 100]), ("00d3", "extract", [25, 50, 70, 100])],
)
def test_recorded_curve_every_boundary(dp, direction, values):
    recorded = bytes.fromhex(CURVES[dp])
    expected = {f"fan_{direction}_stage_{i}": v for i, v in enumerate(values, 1)}
    for split in range(len(recorded) + 1):
        decoder = Decoder()
        assert {
            r.key: r.value
            for r in decoder.feed(recorded[:split]) + decoder.feed(recorded[split:])
        } == expected
    for index in (0, 1, 2, 5, 6, 7, -1):
        corrupt = bytearray(recorded)
        corrupt[index] ^= 1
        assert Decoder().feed(bytes(corrupt)) == []


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, 101.0])
def test_invalid_curve_channel_preserves_neighbors(bad):
    readings = Decoder().feed(frame(0xD2, struct.pack("<4f", 25, bad, 52, 100)))
    assert {r.key: r.value for r in readings} == {
        "fan_supply_stage_1": 25,
        "fan_supply_stage_3": 52,
        "fan_supply_stage_4": 100,
    }


@pytest.mark.parametrize(
    "dp,below,above",
    [(0x110, -1, 101), (0x115, -1, 101), (0x11C, -51, 151)],
)
def test_invalid_threshold_retains_raw(dp, below, above):
    for invalid in (below, above, float("nan"), float("inf")):
        payload = struct.pack("<f", invalid)
        assert {r.key: r.value for r in Decoder().feed(frame(dp, payload))} == {
            f"raw_{dp:04x}": payload.hex()
        }


@pytest.mark.parametrize("dp", [0x115, 0x11C])
def test_heat_pump_threshold_requires_exact_reply(dp):
    payload = struct.pack("<f", 2)
    decoder = Decoder()
    assert decoder.feed(frame(dp, payload, b"\x11\x80\x00")) == []
    assert decoder.feed(frame(dp, payload + bytes(4))) == []
    valid = frame(dp, payload)
    bad_checksum = valid[:-1] + bytes([valid[-1] ^ 1])
    assert decoder.feed(bad_checksum) == []


def test_continuous_run_temperature_can_be_negative():
    readings = Decoder().feed(frame(0x11C, struct.pack("<f", -2.5)))
    assert {r.key: r.value for r in readings} == {
        "raw_011c": "000020c0",
        "heat_pump_continuous_run_threshold": -2.5,
    }


def test_invalid_output_channel_retains_neighbor_and_raw():
    assert {
        r.key: r.value
        for r in Decoder().feed(frame(0x116, struct.pack("<2H", 65535, 90)))
    } == {"raw_0116": "ffff5a00", "max_cooling_output": 90}
    for dp, payload in (
        (0x110, struct.pack("<f", 3)),
        (0x116, struct.pack("<2H", 100, 90)),
    ):
        assert Decoder().feed(frame(dp, payload, b"\x11\x80\x00")) == []
        assert Decoder().feed(frame(dp, payload + bytes(4))) == []


def test_settings_are_optional_without_statistics():
    descriptions = {d.key: d for d in DESCRIPTIONS if d.key in UNITS}
    assert descriptions.keys() == UNITS.keys()
    for description in descriptions.values():
        assert description.entity_registry_enabled_default is False
        assert description.entity_category.value == "diagnostic"
        assert description.state_class is None
        assert description.device_class == (
            SensorDeviceClass.TEMPERATURE_DELTA
            if description.key == "heat_pump_start_threshold"
            else None
        )


async def test_settings_share_existing_freshness(hass):
    runtime = ProxonRuntime(hass, "gateway.test", 4196)
    runtime.connected = True
    readings = Decoder().feed(SETTINGS_FRAMES)
    for reading in readings:
        runtime.values[reading.key] = (reading, time.monotonic())
    for key in UNITS:
        assert runtime.get(key) is not None
        reading, received = runtime.values[key]
        runtime.values[key] = (reading, received - 31)
        assert runtime.get(key) is None
    runtime.connected = False
    assert all(runtime.get(key) is None for key in UNITS)


async def test_enabled_settings_are_real_ha_states_and_disconnect(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="settings-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    entities = {
        key: registry.async_get_or_create(
            "sensor",
            DOMAIN,
            f"settings-unit_{key}",
            config_entry=entry,
            suggested_object_id=f"settings_{key}",
            disabled_by=None,
        ).entity_id
        for key in UNITS
    }
    reader = asyncio.StreamReader()
    reader.feed_data(SETTINGS_FRAMES)

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        for key, entity_id in entities.items():
            state = hass.states.get(entity_id)
            assert state is not None
            assert state.state not in ("unknown", "unavailable")
            assert state.attributes["unit_of_measurement"] == UNITS[key]
            assert "state_class" not in state.attributes
        assert float(hass.states.get(entities["cooling_threshold"]).state) == 3
        assert float(
            hass.states.get(entities["heat_pump_start_threshold"]).state
        ) == pytest.approx(0.399993896)
        assert (
            float(hass.states.get(entities["heat_pump_continuous_run_threshold"]).state)
            == 2
        )
        assert float(hass.states.get(entities["max_cooling_output"]).state) == 90
        reader.feed_eof()
        await hass.async_block_till_done()
        assert all(
            hass.states.get(entity_id).state == "unavailable"
            for entity_id in entities.values()
        )
        assert await hass.config_entries.async_unload(entry.entry_id)
