"""Recorded heating/cooling telemetry and HA behavior on invalid/stale data."""

import asyncio
import struct
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

# Captures (8)/(11), 2026-09-14. Fixed recorded checksums, not generated fixtures.
COOLING = bytes.fromhex("2240001c0500000856b5a9453649")
HEATING = bytes.fromhex("2240001c05000008697997452519")
STOPPED = bytes.fromhex("2240001c0500000800000000ea60")
BYPASS_ON = bytes.fromhex("2240006001000002013bdc")
BYPASS_OFF = bytes.fromhex("224000600100000200cf0d")


def checked(message):
    return message + checksum(message).to_bytes(2, "little")


@pytest.mark.parametrize(
    ("frame", "expected"),
    [
        (COOLING, {"raw_051c": "56b5a945", "compressor_rpm": 5430.6669921875}),
        (HEATING, {"raw_051c": "69799745", "compressor_rpm": 4847.17626953125}),
        (STOPPED, {"raw_051c": "00000000", "compressor_rpm": 0.0}),
        (BYPASS_ON, {"bypass_status": True}),
        (BYPASS_OFF, {"bypass_status": False}),
    ],
)
def test_recorded_telemetry_every_stream_split(frame, expected):
    for split in range(len(frame) + 1):
        decoder = Decoder()
        result = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in result} == expected
        if "bypass_status" in expected:
            assert result[0].value is expected["bypass_status"]


@pytest.mark.parametrize("frame", [COOLING, BYPASS_ON])
def test_checksum_and_identity_validation(frame):
    for index, byte in ((0, 0x11), (1, 0x41), (2, 7), (5, 1), (7, 0)):
        body = bytearray(frame[:-2])
        body[index] = byte
        assert Decoder().feed(checked(body)) == []
    for bit in range(len(frame) * 8):
        damaged = bytearray(frame)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert Decoder().feed(damaged + frame) == Decoder().feed(frame)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, 10001.0])
def test_invalid_rpm_retains_only_raw_diagnostic(value):
    payload = struct.pack("<f", value)
    result = Decoder().feed(checked(COOLING[:8] + payload))
    assert {r.key: r.value for r in result} == {"raw_051c": payload.hex()}


@pytest.mark.parametrize("value", [2, 128, 255])
def test_unknown_bypass_enum_is_not_off(value):
    decoder = Decoder()
    assert decoder.feed(checked(BYPASS_ON[:8] + bytes([value]))) == []
    assert decoder.stats.value_rejected == 1


async def test_ha_defaults_raw_identity_expiry_recovery_and_disconnect(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="stable-unit",
        data={"host": "private.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    # Model a user's existing enabled and renamed raw sensor from 0.4.0.
    raw = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "stable-unit_raw_051c",
        config_entry=entry,
        suggested_object_id="my_existing_compressor_hex",
        disabled_by=None,
    )
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        rpm_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_compressor_rpm"
        )
        bypass_id = registry.async_get_entity_id(
            "binary_sensor", DOMAIN, "stable-unit_bypass_status"
        )
        for entity_id in (rpm_id, bypass_id):
            registered = registry.async_get(entity_id)
            assert registered.disabled_by is None
            assert hass.states.get(entity_id).state == "unavailable"
            assert registered.device_id == registry.async_get(raw.entity_id).device_id
        assert registry.async_get(raw.entity_id).disabled_by is None
        rpm = hass.states.get(rpm_id)
        assert rpm.attributes["unit_of_measurement"] == "rpm"
        assert rpm.attributes["state_class"] == "measurement"
        assert "device_class" not in hass.states.get(bypass_id).attributes

        for frame, expected in ((BYPASS_ON, "on"), (BYPASS_OFF, "off")):
            reader.feed_data(frame + HEATING)
            await hass.async_block_till_done()
            assert hass.states.get(bypass_id).state == expected
            assert float(hass.states.get(rpm_id).state) == pytest.approx(4847.17627)
            assert hass.states.get(raw.entity_id).state == "69799745"

        runtime = entry.runtime_data
        for key in ("compressor_rpm", "bypass_status"):
            reading, timestamp = runtime.values[key]
            runtime.values[key] = (reading, timestamp - 31)
        reader.feed_data(
            checked(COOLING[:8] + struct.pack("<f", float("nan")))
            + checked(BYPASS_ON[:8] + b"\xff")
        )
        await hass.async_block_till_done()
        assert hass.states.get(rpm_id).state == "unavailable"
        assert hass.states.get(bypass_id).state == "unavailable"
        assert hass.states.get(raw.entity_id).state == "0000c07f"
        reader.feed_data(STOPPED + BYPASS_OFF)
        await hass.async_block_till_done()
        assert float(hass.states.get(rpm_id).state) == 0
        assert hass.states.get(bypass_id).state == "off"
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        reader.feed_eof()
        await hass.async_block_till_done()
        for entity_id in (rpm_id, bypass_id):
            assert hass.states.get(entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert not runtime.listeners
        assert runtime.task is None
        assert runtime.timer is None
