"""Experimental observations never claim actuator semantics or freshness."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE


async def test_experimental_bits_raw_context_expiry_and_disconnect(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test",
        unique_id="bits",
        data={"host": "example.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    ids = {
        b: registry.async_get_or_create(
            "binary_sensor",
            DOMAIN,
            f"bits_experimental_0208_bit_{b}",
            config_entry=entry,
            disabled_by=None,
        ).entity_id
        for b in (8, 9, 28)
    }
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert all(hass.states.get(i).state == "unavailable" for i in ids.values())
        # Recorded transition with no allowlisted fan-level interpretation.
        raw = bytes.fromhex("22400008020000081a130090c492")
        reader.feed_data(raw)
        await hass.async_block_till_done()
        for i in ids.values():
            state = hass.states.get(i)
            assert state.state == "on"
            assert state.attributes["payload_hex"] == "1a130090"
            assert state.attributes["status_word_hex"] == "9000131A"
            assert state.attributes["interpretation"] == "unconfirmed"
            assert state.attributes["last_valid_update"]
            assert "device_class" not in state.attributes
        runtime = entry.runtime_data
        assert runtime.get("controller_fan_level") is None
        previous = runtime.values["experimental_status_0208"]
        reader.feed_data(raw[:-1] + bytes([raw[-1] ^ 1]))
        await hass.async_block_till_done()
        assert runtime.values["experimental_status_0208"] == previous
        runtime.values["experimental_status_0208"] = (previous[0], previous[1] - 31)
        runtime._notify()
        for i in ids.values():
            assert hass.states.get(i).state == "unavailable"
            assert hass.states.get(i).attributes.get("payload_hex") is None
        reader.feed_data(bytes.fromhex("22400008020000081a100080b2dc"))
        await hass.async_block_till_done()
        assert all(hass.states.get(i).state == "off" for i in ids.values())
        reader.feed_eof()
        await hass.async_block_till_done()
        assert all(hass.states.get(i).state == "unavailable" for i in ids.values())
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        assert await hass.config_entries.async_unload(entry.entry_id)
