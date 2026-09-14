"""Recorded controller levels/control values; bounded, opt-in HA diagnostics."""

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

# Fixed recorded frames/checksums from captures 1, 5, 7, 9, 10, 14, 16, 18.
LEVELS = [
    ("22400008020000081a100080b2dc", 3),
    ("22400008020000080a100080f28f", 1),
    ("2240000802000008221400803934", 4),
    ("2240000802000008221500806ff9", 4),
    ("22400008020000082211008084cd", 4),
    ("22400008020000081a130080d98b", 3),
    ("224000080200000822100080d200", 4),
    ("22400008020000081210008012f5", 2),
]
CONTROLS = [
    ("224000d7000000100080a2450080a245a292", (5200.0, 5200.0)),
    ("224000d70000001000401c4500401c452299", (2500.0, 2500.0)),
    ("224000d70000001000401c4600401c465b23", (10000.0, 10000.0)),
    ("224000d70000001000007a4500007a459941", (4000.0, 4000.0)),
    ("224000d70000001000401c4600c0da450bbb", (10000.0, 7000.0)),
]
CONTROL_KEYS = ("fan_supply_control", "fan_extract_control")
KEYS = ("controller_fan_level", *CONTROL_KEYS)


def checked(body):
    """Synthetic invalid data gets a valid CRC to exercise value validation."""
    return body + checksum(body).to_bytes(2, "little")


@pytest.mark.parametrize("raw,expected", LEVELS + CONTROLS)
def test_recorded_diagnostics_at_every_stream_split(raw, expected):
    frame = bytes.fromhex(raw)
    expected_values = (
        dict(zip(CONTROL_KEYS, expected, strict=True))
        if isinstance(expected, tuple)
        else {"controller_fan_level": expected}
    )
    for split in range(len(frame) + 1):
        decoder = Decoder()
        readings = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in readings} == expected_values


@pytest.mark.parametrize("raw", [LEVELS[0][0], CONTROLS[0][0]])
def test_invalid_identity_and_crc_rejected_with_recovery(raw):
    frame = bytes.fromhex(raw)
    for index, value in ((0, 0x11), (1, 0x41), (2, 1), (5, 1), (7, 0)):
        body = bytearray(frame[:-2])
        body[index] = value
        assert Decoder().feed(checked(body)) == []
    for bit in range(len(frame) * 8):
        damaged = bytearray(frame)
        damaged[bit // 8] ^= 1 << (bit % 8)
        assert Decoder().feed(damaged + frame) == Decoder().feed(frame)


@pytest.mark.parametrize(
    "status",
    [
        0,
        0xFFFFFFFF,
        0x80001002,
        0x8000102A,
        0x80001032,
        0x8000103A,
        0x8000931A,
        0x8080121A,
        0x8000135A,
    ],
)
def test_unknown_status_is_not_a_guessed_level(status):
    header = bytes.fromhex(LEVELS[0][0])[:8]
    assert Decoder().feed(checked(header + struct.pack("<I", status))) == []


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1.0, 10001.0])
@pytest.mark.parametrize("channel", [0, 1])
def test_invalid_control_does_not_hide_valid_sibling(invalid, channel):
    values = [5200.25, 5200.25]
    values[channel] = invalid
    header = bytes.fromhex(CONTROLS[0][0])[:8]
    readings = Decoder().feed(checked(header + struct.pack("<2f", *values)))
    assert {r.key: r.value for r in readings} == {CONTROL_KEYS[1 - channel]: 5200.25}


async def test_enabled_diagnostics_missing_expiry_recovery_disconnect(hass, frames):
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
    ids = {
        key: registry.async_get_or_create(
            "sensor",
            DOMAIN,
            f"stable-unit_{key}",
            config_entry=entry,
            suggested_object_id=f"my_{key}",
            disabled_by=None,
        ).entity_id
        for key in KEYS
    }
    with patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        for entity_id in ids.values():
            state = hass.states.get(entity_id)
            assert state.state == "unavailable"
            assert registry.async_get(entity_id).disabled_by is None
            assert "unit_of_measurement" not in state.attributes
            assert "state_class" not in state.attributes
            assert "device_class" not in state.attributes

        valid = bytes.fromhex(LEVELS[3][0] + CONTROLS[-1][0])
        reader.feed_data(valid)
        await hass.async_block_till_done()
        assert [float(hass.states.get(ids[k]).state) for k in KEYS] == [4, 10000, 7000]
        runtime = entry.runtime_data
        invalid = checked(valid[:8] + b"\xff" * 4)
        invalid += checked(bytes.fromhex(CONTROLS[0][0])[:8] + b"\xff" * 8)
        previous = {key: runtime.values[key] for key in KEYS}
        reader.feed_data(invalid)
        await hass.async_block_till_done()
        assert {key: runtime.values[key] for key in KEYS} == previous
        for key in KEYS:
            reading, timestamp = runtime.values[key]
            runtime.values[key] = (reading, timestamp - 31)
        runtime._notify()
        assert all(hass.states.get(i).state == "unavailable" for i in ids.values())
        reader.feed_data(valid)
        await hass.async_block_till_done()
        assert [float(hass.states.get(ids[k]).state) for k in KEYS] == [4, 10000, 7000]
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        reader.feed_eof()
        await hass.async_block_till_done()
        assert all(hass.states.get(i).state == "unavailable" for i in ids.values())
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert not runtime.listeners
