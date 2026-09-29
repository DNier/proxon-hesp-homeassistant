"""BDE valve indication remains independent of compressor and cooling activity."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

# Recorded full frames, including the valve hold after reported compressor stop.
FRAMES = [
    ("2240006c00000008250000000da9", "off"),
    ("2240006c000000082700000065a3", "off"),
    ("2240006c00000008a70000004738", "off"),
    ("2240006c00000008250200003033", "on"),
    ("2240006c00000008270200005839", "on"),
    ("2240006c00000008a70200007aa2", "on"),
]


def checked(body):
    return body + checksum(body).to_bytes(2, "little")


@pytest.mark.parametrize("raw,state", FRAMES)
def test_recorded_valve_frames_preserve_raw_at_every_split(raw, state):
    frame = bytes.fromhex(raw)
    for split in range(len(frame) + 1):
        decoder = Decoder()
        readings = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in readings} == {"raw_006c": raw[16:24]}


async def test_valve_lifecycle_and_independence(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="valve-unit",
        title="PROXON",
        data={"host": "example.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_id = registry.async_get_entity_id(
            "binary_sensor", DOMAIN, "valve-unit_heat_cool_valve"
        )
        registered = registry.async_get(entity_id)
        assert registered.disabled_by == er.RegistryEntryDisabler.INTEGRATION
        # Enable through the registry and reload, as a user would.
        registry.async_update_entity(entity_id, disabled_by=None)
        reader.feed_data(frames["0xe1"])
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "unavailable"
        for raw, state in FRAMES:
            reader.feed_data(bytes.fromhex(raw))
            await hass.async_block_till_done()
            result = hass.states.get(entity_id)
            assert result.state == state
            assert result.attributes["payload_hex"] == raw[16:24]
            assert result.attributes["interpretation"] == "bde_valve_indication"
            assert "device_class" not in result.attributes
        runtime = entry.runtime_data
        previous = runtime.values["raw_006c"]
        good = bytes.fromhex(FRAMES[-1][0])
        # Wrong node, reserved bytes and length must never refresh the source.
        for index, value in ((0, 0x11), (2, 7), (5, 1), (7, 6)):
            body = bytearray(good[:-2])
            body[index] = value
            reader.feed_data(checked(body))
        reader.feed_data(good[:-1] + bytes([good[-1] ^ 1]))
        await hass.async_block_till_done()
        assert runtime.values["raw_006c"] == previous
        # Unknown but checksum-valid words invalidate the interpretation immediately.
        for payload in ("00000000", "ffffffff", "25020100"):
            reader.feed_data(checked(good[:8] + bytes.fromhex(payload)))
            await hass.async_block_till_done()
            assert hass.states.get(entity_id).state == "unavailable"
            assert runtime.get("raw_006c").value == payload
        # Recorded post-stop hold: RPM zero does not clear the valve indication.
        reader.feed_data(
            bytes.fromhex("2240001c0500000800000000ea60") + bytes.fromhex(FRAMES[3][0])
        )
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "on"
        reading, stamp = runtime.values["raw_006c"]
        runtime.values["raw_006c"] = (reading, stamp - 31)
        runtime._notify()
        assert hass.states.get(entity_id).state == "unavailable"
        reader.feed_data(bytes.fromhex(FRAMES[0][0]))
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "off"
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)
