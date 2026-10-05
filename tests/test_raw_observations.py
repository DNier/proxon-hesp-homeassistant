"""Exact raw identities, unchanged-sample freshness and passive HA lifecycle."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

# Synthetic, non-identifying payloads. Bit patterns are not actuator evidence.
SOURCES = {
    "raw_118000_01f8": ("118000", 0x01F8, "00080000"),
    "raw_118000_03b6": ("118000", 0x03B6, "02000000"),
    "raw_118007_0191": ("118007", 0x0191, "0200"),
    "raw_0208": ("224000", 0x0208, "1a120080"),
    "raw_006c": ("224000", 0x006C, "e7000000"),
}


def checked(body):
    return body + checksum(body).to_bytes(2, "little")


def source_frame(source, payload=None):
    identity, dp, original = source
    wire_payload = bytes.fromhex(original if payload is None else payload)
    return checked(
        bytes.fromhex(identity)
        + dp.to_bytes(2, "little")
        + b"\x00\x00"
        + bytes([2 * len(wire_payload)])
        + wire_payload
    )


@pytest.mark.parametrize("key,source", SOURCES.items())
def test_full_raw_payload_at_every_stream_boundary(key, source):
    frame = source_frame(source)
    for split in range(len(frame) + 1):
        decoder = Decoder()
        readings = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in readings}[key] == source[2]
        assert decoder.stats.accepted == 1
        values = {r.key: r.value for r in readings}
        if key == "raw_118000_01f8":
            assert values["intensive_ventilation"] is False
        if key == "raw_0208":
            assert values["experimental_status_0208"] == source[2]
            assert "controller_fan_level" not in values


@pytest.mark.parametrize("key,source", SOURCES.items())
def test_header_length_reserved_and_corruption_do_not_publish(key, source):
    frame = source_frame(source)
    wrong_node = 0 if frame[2] else 7
    for index, value in ((0, 0x10), (1, 0x81), (2, wrong_node), (5, 1), (7, 0)):
        body = bytearray(frame[:-2])
        body[index] = value
        decoder = Decoder()
        assert decoder.feed(checked(body)) == []
        assert {r.key: r.value for r in decoder.feed(frame)}[key] == source[2]
    for bit in range(len(frame) * 8):
        damaged = bytearray(frame)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert Decoder().feed(damaged + frame) == Decoder().feed(frame)


@pytest.mark.parametrize("key,source", SOURCES.items())
def test_raw_zero_leading_zeros_and_unknown_bits_are_preserved(key, source):
    size = len(bytes.fromhex(source[2]))
    for payload in (bytes(size), b"\xff" * size, b"\x01" + bytes(size - 1)):
        values = {
            r.key: r.value for r in Decoder().feed(source_frame(source, payload.hex()))
        }
        assert values[key] == payload.hex()


async def test_ha_raw_freshness_unchanged_payload_expiry_disconnect_and_no_writes(
    hass, frames
):
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="raw-observation-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    ids = {
        key: registry.async_get_or_create(
            "sensor",
            DOMAIN,
            f"raw-observation-unit_{key}",
            config_entry=entry,
            disabled_by=None,
        ).entity_id
        for key in SOURCES
    }
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        for entity_id in ids.values():
            registered = registry.async_get(entity_id)
            assert registered.entity_category.value == "diagnostic"
            state = hass.states.get(entity_id)
            assert state.state == "unavailable"
            assert "last_valid_update" not in state.attributes
            assert "state_class" not in state.attributes
            assert "unit_of_measurement" not in state.attributes

        stream = b"".join(source_frame(source) for source in SOURCES.values())
        reader.feed_data(stream)
        await hass.async_block_till_done()
        before = {}
        for key, entity_id in ids.items():
            state = hass.states.get(entity_id)
            assert state.state == SOURCES[key][2]
            assert state.attributes["source_header"] == SOURCES[key][0]
            assert state.attributes["dp_id"] == f"0x{SOURCES[key][1]:04X}"
            assert state.attributes["payload_length"] == len(
                bytes.fromhex(SOURCES[key][2])
            )
            before[key] = state.attributes["last_valid_update"]
            assert datetime.fromisoformat(before[key]).utcoffset() is not None

        # Same valid payload is a new observation, not a state edge.
        reader.feed_data(stream)
        await hass.async_block_till_done()
        previous_samples = {}
        previous_stamps = {}
        for key, entity_id in ids.items():
            state = hass.states.get(entity_id)
            assert state.state == SOURCES[key][2]
            stamp = state.attributes["last_valid_update"]
            assert datetime.fromisoformat(stamp) > datetime.fromisoformat(before[key])
            previous_samples[key] = runtime.values[key]
            previous_stamps[key] = stamp

        for source in SOURCES.values():
            valid = source_frame(source)
            reader.feed_data(valid[:-1] + bytes([valid[-1] ^ 1]))
        await hass.async_block_till_done()
        for key, entity_id in ids.items():
            assert runtime.values[key] == previous_samples[key]
            assert (
                hass.states.get(entity_id).attributes["last_valid_update"]
                == previous_stamps[key]
            )

        # A stale raw point becomes unavailable even while another stays fresh.
        key = "raw_118007_0191"
        reading, timestamp = runtime.values[key]
        runtime.values[key] = (reading, timestamp - 31)
        runtime._notify()
        assert hass.states.get(ids[key]).state == "unavailable"
        assert "last_valid_update" not in hass.states.get(ids[key]).attributes
        assert hass.states.get(ids["raw_0208"]).state == SOURCES["raw_0208"][2]
        reader.feed_data(source_frame(SOURCES[key]))
        await hass.async_block_till_done()
        assert hass.states.get(ids[key]).state == SOURCES[key][2]

        reader.feed_eof()
        await hass.async_block_till_done()
        assert all(
            hass.states.get(entity_id).state == "unavailable"
            for entity_id in ids.values()
        )
        assert all(
            "last_valid_update" not in hass.states.get(entity_id).attributes
            for entity_id in ids.values()
        )
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.task is None and runtime.timer is None
        assert not runtime.listeners
