"""Real HA sensors and registry backed by an in-memory passive TCP stream."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.diagnostics import async_get_config_entry_diagnostics


async def test_setup_values_availability_registry_and_unload(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(b"".join(frames.values()))
    controller = json.loads(
        (Path(__file__).parent / "fixtures/controller_frames.json").read_text()
    )
    reader.feed_data(b"".join(bytes.fromhex(frame) for frame in controller.values()))
    closed = asyncio.Event()

    @asynccontextmanager
    async def receiver(*args):
        try:
            yield reader
        finally:
            closed.set()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="stable-unit",
        data={"host": "private.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        fan_id = registry.async_get_entity_id("sensor", DOMAIN, "stable-unit_fan_level")
        mode_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_operating_mode"
        )
        assert hass.states.get(fan_id).state == "3"
        assert hass.states.get(mode_id).state == "eco_summer"
        device = dr.async_get(hass).async_get(registry.async_get(fan_id).device_id)
        filter_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "stable-unit_filter_days"
        )
        assert hass.states.get(filter_id).state == "114"
        assert hass.states.get(filter_id).attributes["unit_of_measurement"] == "d"
        raw_id = registry.async_get_entity_id("sensor", DOMAIN, "stable-unit_raw_0116")
        assert registry.async_get(raw_id).disabled_by is not None
        assert hass.states.get(raw_id) is None
        assert device.model == "PROXON P-Serie (HESP)"
        assert len(er.async_entries_for_config_entry(registry, entry.entry_id)) == 32
        runtime = entry.runtime_data
        # One value expires while another remains fresh.
        reading, timestamp = runtime.values["fan_level"]
        runtime.values["fan_level"] = (reading, timestamp - 31)
        runtime._notify()
        assert hass.states.get(fan_id).state == "unavailable"
        assert hass.states.get(mode_id).state == "eco_summer"
        diagnostic = await async_get_config_entry_diagnostics(hass, entry)
        assert "private.test" not in str(diagnostic)
        assert "stable-unit" not in str(diagnostic)
        assert diagnostic["application_bytes_sent"] == 0
        assert diagnostic["statistics"]["accepted"] == 32
        reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.get(mode_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.task is None
        assert runtime.timer is None
        assert closed.is_set()
