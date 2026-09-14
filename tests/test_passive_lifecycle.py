"""The real HA lifecycle and capture buttons never send gateway payloads."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE


async def test_receive_capture_reconnect_reload_remain_read_only(hass, frames):
    streams = []
    reconnected = asyncio.Event()

    async def connect(*args):
        reader = asyncio.StreamReader()
        reader.feed_data(b"".join(frames.values()))
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        streams.append((reader, writer))
        if len(streams) == 2:
            reconnected.set()
        return reader, writer

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="passive-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    with patch("asyncio.open_connection", side_effect=connect):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        ids = {
            entity.unique_id: entity.entity_id
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert len(ids) == 54
        fan_id = ids["passive-unit_fan_level"]
        registry.async_update_entity(fan_id, name="My ventilation level")

        # Upgrading users must not be able to invoke the retired experiment.
        for service in (
            "prepare_target_temperature_test",
            "send_target_temperature_test",
        ):
            assert not hass.services.has_service(DOMAIN, service)
            with pytest.raises(ServiceNotFound):
                await hass.services.async_call(
                    DOMAIN, service, {"config_entry_id": entry.entry_id}, blocking=True
                )

        async def press(action):
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": ids[f"passive-unit_capture_{action}"]},
                blocking=True,
            )

        runtime = entry.runtime_data
        await press("start")
        streams[0][0].feed_data(b"".join(frames.values()))
        await hass.async_block_till_done()
        assert runtime.capture.export()["bytes"] > 0
        await press("stop")
        assert runtime.capture.export()["status"] == "manual"
        await press("clear")
        assert runtime.capture.export()["chunks"] == []
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        assert "target_temperature_test" not in runtime.diagnostics()

        await press("start")
        streams[0][0].feed_eof()
        await asyncio.wait_for(reconnected.wait(), 5)
        await hass.async_block_till_done()
        assert runtime.reconnects == 1
        assert runtime.connected
        assert runtime.capture.export()["status"] == "disconnected"
        assert hass.states.get(fan_id).state == "3"

        await press("start")
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert len(streams) == 3
        assert entry.runtime_data is not runtime
        assert runtime.task is None and runtime.timer is None
        assert runtime.capture.timer is None
        assert entry.runtime_data.capture.export()["chunks"] == []
        assert ids == {
            entity.unique_id: entity.entity_id
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert registry.async_get(fan_id).name == "My ventilation level"
        assert hass.states.get(fan_id).state == "3"

        reloaded_runtime = entry.runtime_data
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert reloaded_runtime.task is None and reloaded_runtime.timer is None
        for _, writer in streams:
            writer.write.assert_not_called()
            writer.writelines.assert_not_called()
            writer.close.assert_called_once()
            writer.wait_closed.assert_awaited_once()
