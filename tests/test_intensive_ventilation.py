"""Recorded BDE flags, independent bits, and real HA binary sensor lifecycle."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

# Minimal non-identifying recorded telegrams, 2026-09-14, captures (10)/(14).
OFF = bytes.fromhex("118000f80100000800000000a1fd")
ON = bytes.fromhex("118000f8010000084000000030b0")
OTHER_BIT = bytes.fromhex("118000f801000008000800007794")


def checked_frame(message):
    """Synthetic mutations use valid checksums to isolate header/bit handling."""
    return message + checksum(message).to_bytes(2, "little")


@pytest.mark.parametrize(
    ("frame", "expected"), [(OFF, False), (ON, True), (OTHER_BIT, False)]
)
def test_recorded_flags_across_every_stream_split(frame, expected):
    for split in range(len(frame) + 1):
        decoder = Decoder()
        readings = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert len(readings) == 1
        assert readings[0].key == "intensive_ventilation"
        assert readings[0].value is expected


def test_other_bits_do_not_hide_intensive_ventilation():
    # Synthetic combination; simultaneous flags are not claimed as field evidence.
    combined = checked_frame(ON[:8] + bytes.fromhex("40080000"))
    assert Decoder().feed(combined)[0].value is True


def test_recorded_automatic_end_during_cooling_keeps_request_and_rpm_separate():
    # Capture (18): BDE display stays at 4, but its HESP request returns to 3.
    # Actual fan speeds stay high; neither is a substitute for the intensive bit.
    fan_request = bytes.fromhex("118000e1000000040300dba6")
    actual_rpm = bytes.fromhex("224000c9000000101c92174535771e452f1f")
    controller_flags = bytes.fromhex("2240000802000008221500806ff9")
    data = ON + OFF + fan_request + actual_rpm + controller_flags
    for chunk_size in (1, 7, len(data)):
        decoder = Decoder()
        received = []
        for offset in range(0, len(data), chunk_size):
            received.extend(decoder.feed(data[offset : offset + chunk_size]))
        assert [r.value for r in received if r.key == "intensive_ventilation"] == [
            True,
            False,
        ]
        values = {r.key: r.value for r in received}
        assert values["fan_level"] == 3
        assert values["controller_fan_level"] == 4
        assert values["fan_supply_rpm"] == pytest.approx(2425.1318359375)
        assert values["fan_extract_rpm"] == pytest.approx(2535.450439453125)
        assert decoder.stats.checksum_rejected == 0


def test_wrong_source_length_and_checksum_cannot_update_status():
    wrong_frames = [
        checked_frame(bytes.fromhex("224000") + ON[3:-2]),
        checked_frame(bytes.fromhex("118007") + ON[3:-2]),
        checked_frame(ON[:7] + b"\x04\x40\x00"),
        ON[:-1] + bytes([ON[-1] ^ 1]),
    ]
    for frame in wrong_frames:
        decoder = Decoder()
        assert decoder.feed(frame) == []
        assert decoder.feed(OFF)[0].value is False


async def test_binary_sensor_missing_on_off_stale_disconnect_and_unload(hass, frames):
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
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_id = registry.async_get_entity_id(
            "binary_sensor", DOMAIN, "stable-unit_intensive_ventilation"
        )
        fan_id = registry.async_get_entity_id("sensor", DOMAIN, "stable-unit_fan_level")
        registered = registry.async_get(entity_id)
        assert registered.disabled_by is None
        assert registered.device_id == registry.async_get(fan_id).device_id
        assert hass.states.get(entity_id).state == "unavailable"

        for frame, expected in [(ON, "on"), (OFF, "off"), (OTHER_BIT, "off")]:
            reader.feed_data(frame)
            await hass.async_block_till_done()
            assert hass.states.get(entity_id).state == expected

        runtime = entry.runtime_data
        reading, timestamp = runtime.values["intensive_ventilation"]
        runtime.values["intensive_ventilation"] = (reading, timestamp - 31)
        runtime._notify()
        assert hass.states.get(entity_id).state == "unavailable"
        assert hass.states.get(fan_id).state == "3"

        reader.feed_data(ON)
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "on"
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.task is None
        assert runtime.timer is None
        assert not runtime.listeners
