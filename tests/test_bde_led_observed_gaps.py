"""Synthetic receiver regressions for the newly observed finite LED contexts.

The source frames reuse published vectors. Changed payloads, their checksums,
combined sequences and receipt times below are synthetic, not new captures.
"""

import asyncio
import json
import struct
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.bde_display import BdeDisplay
from custom_components.proxon_hesp.const import (
    CONF_P2_REFERENCE_DISPLAY,
    DOMAIN,
    PROFILE,
)
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

PUBLIC_FRAMES = json.loads(
    (Path(__file__).parent / "fixtures/bde_display_frames.json").read_text()
)["frames"]
RPM, MODE, VALVES, STATUS = (bytes.fromhex(frame["hex"]) for frame in PUBLIC_FRAMES[:4])


def synthetic_payload(frame: bytes, payload: bytes) -> bytes:
    body = frame[:8] + payload
    return body + checksum(body).to_bytes(2, "little")


STATUS_12930082 = synthetic_payload(STATUS, bytes.fromhex("12930082"))
STATUS_12930080 = synthetic_payload(STATUS, bytes.fromhex("12930080"))
STATUS_12930092 = synthetic_payload(STATUS, bytes.fromhex("12930092"))
VALVES_67 = synthetic_payload(VALVES, bytes.fromhex("67000000"))
VALVES_47 = synthetic_payload(VALVES, bytes.fromhex("47000000"))
VALVES_A7 = synthetic_payload(VALVES, bytes.fromhex("a7000000"))
UNOBSERVED_VALVES = synthetic_payload(VALVES, bytes.fromhex("25000000"))
COMFORT = synthetic_payload(MODE, bytes.fromhex("0300"))
DARK_STATUS = synthetic_payload(STATUS, bytes.fromhex("0a100080"))
OBSERVED_CONTEXTS = (
    (MODE, STATUS_12930080, VALVES, RPM),
    (MODE, STATUS_12930082, VALVES_67, RPM),
    (MODE, STATUS_12930082, VALVES_47, RPM),
    (MODE, STATUS_12930092, VALVES, RPM),
)


@pytest.fixture(
    params=OBSERVED_CONTEXTS,
    ids=("12930080-27", "12930082-67", "12930082-47", "12930092-27"),
)
def context(request):
    return request.param


@pytest.fixture
def stream():
    display = BdeDisplay(p2_reference=True, supports_green_led=True)
    clock = SimpleNamespace(now=0.0)
    decoder = Decoder(
        lambda source, readings: display.observe(source, readings, clock.now)
    )

    def feed(data: bytes, at: float) -> None:
        clock.now = at
        decoder.feed(data)

    return display, feed


def test_observed_unavailable_sequences_keep_the_led_on(stream):
    display, feed = stream
    feed(MODE + STATUS_12930082 + VALVES + RPM, 0)
    assert display.green_led(0) is True
    for at, frame in (
        (1, VALVES_67),
        (2, VALVES_47),
        (3, VALVES),
        (4, STATUS_12930080),
    ):
        feed(frame, at)
        assert display.green_led(at) is True
        assert display.green_led_basis(at) == "display_reference"
    assert display.green_led_expires_at == 8


def test_morning_valve_transition_and_long_fresh_phase_keep_the_led_on(stream):
    display, feed = stream
    feed(MODE + STATUS_12930092 + VALVES_A7 + RPM, 0)
    assert display.green_led(0) is True
    feed(VALVES, 1)
    assert display.green_led(1) is True
    # Synthetic 102-second valve phase: fresh receipts, not a grace period.
    for at in range(6, 102, 5):
        feed(b"".join(OBSERVED_CONTEXTS[3]), at)
        assert display.green_led(at) is True
        assert display.green_led_basis(at) == "display_reference"
        assert display.value(at) == ("heating" if at >= 16 else None)
        assert display.fan_level(at) == 2
    feed(VALVES_A7, 103)
    assert display.green_led(103) is True
    assert display.green_led_basis(103) == "display_reference"
    assert display.value(103) == "heating"
    assert display.fan_level(103) == 2
    assert display.value(108) == "heating"
    assert display.value(108.000001) is None
    assert display.fan_level(108) == 2
    assert display.fan_level(108.000001) is None
    assert display.green_led(109) is True
    assert display.green_led(109.000001) is None


@pytest.mark.parametrize(
    "source_index", range(4), ids=("mode", "status", "valves", "rpm")
)
def test_each_source_is_required_and_keeps_its_own_deadline(
    stream, context, source_index
):
    display, feed = stream
    others = b"".join(
        frame for index, frame in enumerate(context) if index != source_index
    )
    feed(others, 0)
    assert display.green_led(0) is None
    feed(context[source_index], 1)
    assert display.green_led(1) is True
    assert display.green_led_expires_at == 8
    feed(others, 7)
    assert display.green_led(9) is True
    assert display.green_led(9.000001) is None
    feed(others, 9.000001)
    assert display.green_led(9.000001) is None
    feed(context[source_index], 10)
    assert display.green_led(10) is True


@pytest.mark.parametrize("value", (0, -1, float("nan"), float("inf"), 10001))
def test_zero_or_invalid_rpm_removes_the_led_reference(stream, context, value):
    display, feed = stream
    feed(b"".join(context), 0)
    assert display.green_led(0) is True
    feed(synthetic_payload(RPM, struct.pack("<f", value)), 1)
    assert display.green_led(1) is None
    assert display.green_led_basis(1) is None
    feed(RPM, 2)
    assert display.green_led(2) is True


def test_neighboring_status_and_unobserved_valves_are_not_admitted(stream, context):
    display, feed = stream
    feed(b"".join(context), 0)
    assert display.green_led(0) is True
    word = int.from_bytes(context[1][8:-2], "little")
    feed(synthetic_payload(STATUS, (word ^ 1).to_bytes(4, "little")), 1)
    assert display.green_led(1) is None
    feed(context[1], 2)
    assert display.green_led(2) is True
    feed(UNOBSERVED_VALVES, 3)
    assert display.green_led(3) is None
    feed(context[2], 4)
    assert display.green_led(4) is True


def test_off_mode_changes_and_reset_cannot_reuse_the_previous_reference(
    stream, context
):
    display, feed = stream
    feed(b"".join(context), 0)
    assert display.green_led(0) is True
    feed(DARK_STATUS, 1)
    assert display.green_led(1) is False
    assert display.green_led_basis(1) == "display_reference"
    feed(context[1], 2)
    assert display.green_led(2) is True
    feed(COMFORT, 3)
    assert display.green_led(3) is None
    feed(MODE, 4)
    assert display.green_led(4) is None
    feed(context[1], 5)
    assert display.green_led(5) is True
    display.reset()
    assert display.green_led(5) is None
    feed(context[2] + RPM, 6)
    assert display.green_led(6) is None
    feed(MODE + context[1], 7)
    assert display.green_led(7) is True


def test_p2_variant_changes_forget_the_old_source_snapshot(stream, context):
    display, feed = stream
    feed(b"".join(context), 0)
    assert display.green_led(0) is True
    display.configure_p2_reference(False)
    feed(b"".join(context), 1)
    assert display.green_led(1) is None
    display.configure_p2_reference(True)
    assert display.green_led(1) is None
    feed(b"".join(context), 2)
    assert display.green_led(2) is True


@pytest.mark.parametrize(
    "source_index", range(4), ids=("mode", "status", "valves", "rpm")
)
def test_nonmonotonic_receipt_cannot_refresh_a_reference(stream, context, source_index):
    display, feed = stream
    feed(b"".join(context), 10)
    assert display.green_led(10) is True
    feed(context[source_index], 9)
    assert display.green_led(9) is None
    assert display.green_led_basis(9) is None
    feed(b"".join(context), 11)
    assert display.green_led(11) is True


def test_only_the_separately_observed_morning_context_assigns_heating_and_fan(
    stream, context
):
    display, feed = stream
    morning = context[1] == STATUS_12930092
    for at in (0, 5, 10, 15):
        feed(b"".join(context), at)
        assert display.green_led(at) is True
        assert display.value(at) == ("heating" if morning and at == 15 else None)
        assert display.fan_level(at) == (2 if morning else None)
    if morning:
        assert display.value(22) == "heating"
        assert display.value(22.000001) is None
        assert display.fan_level(22) == 2
        assert display.fan_level(22.000001) is None
        assert display.green_led(23) is True
        assert display.green_led(23.000001) is None


async def test_ha_receiver_publishes_the_references_and_invalidates_on_disconnect(
    hass, frames
):
    loop = asyncio.get_running_loop()
    start = float(int(loop.time()))
    clock = SimpleNamespace(now=start)
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="observed-led-gaps",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
        options={CONF_P2_REFERENCE_DISPLAY: True},
    )
    entry.add_to_hass(hass)
    registered = er.async_get(hass).async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "observed-led-gaps_bde_green_led",
        config_entry=entry,
        disabled_by=None,
    )
    sensor_entities = {
        key: er.async_get(hass).async_get_or_create(
            "sensor",
            DOMAIN,
            f"observed-led-gaps_{key}",
            config_entry=entry,
            disabled_by=None,
        )
        for key in ("bde_operating_display", "controller_fan_level")
    }

    async def receive_at(elapsed: float, data: bytes, expected: str) -> None:
        clock.now = start + elapsed
        reader.feed_data(data)
        await hass.async_block_till_done()
        assert hass.states.is_state(registered.entity_id, expected)

    with (
        patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver),
        patch(
            "custom_components.proxon_hesp.coordinator.time",
            SimpleNamespace(monotonic=lambda: clock.now),
        ),
        patch(
            "custom_components.proxon_hesp.binary_sensor.time",
            SimpleNamespace(monotonic=lambda: clock.now),
        ),
        patch.object(loop, "time", lambda: clock.now),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        for at, context in enumerate(OBSERVED_CONTEXTS, start=1):
            await receive_at(at, b"".join(context), "on")
            state = hass.states.get(registered.entity_id)
            assert state.attributes["state_basis"] == "display_reference"
            assert not state.attributes.get("assumed_state", False)
        await receive_at(5, UNOBSERVED_VALVES, "unavailable")
        await receive_at(6, b"".join(OBSERVED_CONTEXTS[0]), "on")
        await receive_at(7, DARK_STATUS, "off")
        await receive_at(8, STATUS_12930080, "on")
        await receive_at(9, MODE + STATUS_12930092 + VALVES_A7 + RPM, "on")
        await receive_at(10, VALVES, "on")
        for at in range(15, 111, 5):
            await receive_at(at, b"".join(OBSERVED_CONTEXTS[3]), "on")
            state = hass.states.get(registered.entity_id)
            assert state.attributes["state_basis"] == "display_reference"
            assert not state.attributes.get("assumed_state", False)
            assert hass.states.is_state(
                sensor_entities["controller_fan_level"].entity_id, "2"
            )
            assert hass.states.is_state(
                sensor_entities["bde_operating_display"].entity_id,
                "heating" if at >= 25 else "unavailable",
            )
        await receive_at(112, VALVES_A7, "on")
        assert hass.states.is_state(
            sensor_entities["bde_operating_display"].entity_id, "heating"
        )
        runtime = entry.runtime_data
        reader.feed_eof()
        await hass.async_block_till_done()
        assert not runtime.connected
        assert hass.states.is_state(registered.entity_id, "unavailable")
        assert all(
            hass.states.is_state(entity.entity_id, "unavailable")
            for entity in sensor_entities.values()
        )
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.timer is None
