"""Public wire vectors, fail-closed source checks and HA lifecycle regressions."""

import asyncio
import json
import struct
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    get_scheduled_timer_handles,
)

from custom_components.proxon_hesp.bde_display import BdeDisplay
from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from custom_components.proxon_hesp.sensor import DESCRIPTIONS, ProxonSensor

RECORDED = json.loads(
    (Path(__file__).parent / "fixtures/bde_display_frames.json").read_text()
)["frames"]
FAN3_PUBLIC_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/bde_display_fan3_frames.json").read_text()
)
FAN3_PUBLIC_VECTORS = FAN3_PUBLIC_FIXTURE["sequences"]
# Original checksums from the reviewed minimal reference sequence.
RPM, MODE, VALVES, STATUS = [bytes.fromhex(item["hex"]) for item in RECORDED[:4]]
SOURCES = (MODE, STATUS, VALVES, RPM)
ALL = b"".join(SOURCES)
# Reuse published source payloads; fan-level-3 replay timing is synthetic.
FAN3_SOURCES = tuple(
    next(
        frame
        for item in FAN3_PUBLIC_VECTORS[0]["frames"]
        if (frame := bytes.fromhex(item["hex"]))[:8] == source[:8]
    )
    for source in SOURCES
)
STOPPED = bytes.fromhex("2240001c0500000800000000ea60")
A7 = bytes.fromhex("2240006c00000008a70000004738")
STATUS_9200131A = bytes.fromhex("22400008020000081a130092bd31")


def checked(body):
    """Create synthetic negative cases; positive fixtures keep recorded checksums."""
    return body + checksum(body).to_bytes(2, "little")


STATUS_8200111A = checked(STATUS[:8] + bytes.fromhex("1a110082"))


@pytest.fixture(params=(SOURCES, FAN3_SOURCES), ids=("fan-level-2", "fan-level-3"))
def heating_sources(request):
    return request.param


@pytest.fixture
def display_stream():
    display = BdeDisplay()
    clock = SimpleNamespace(now=0.0)
    decoder = Decoder(
        lambda source, readings: display.observe(source, readings, clock.now)
    )

    def feed(data, at):
        clock.now = at
        return decoder.feed(data)

    return display, feed, decoder


def stabilize(feed, start=0.0, sources=SOURCES):
    for at in (start, start + 5, start + 10, start + 15):
        feed(b"".join(sources), at)


def test_recorded_sequence_qualifies_on_fresh_receipt_after_15_seconds(display_stream):
    display, feed, _ = display_stream
    first_heating = None
    for item in RECORDED:
        now = item["elapsed_ms"] / 1000
        feed(bytes.fromhex(item["hex"]), now)
        value = display.value(now)
        if now < 16.669:
            assert value is None
        else:
            assert value == "heating"
            if first_heating is None:
                first_heating = now
    assert first_heating == 16.669
    assert display.value(42.666) == "heating"
    # Valve/status receipts are older than the final RPM/mode updates.
    assert display.value(43.578999) == "heating"
    assert display.value(43.579001) is None


@pytest.mark.parametrize("sequence", FAN3_PUBLIC_VECTORS, ids=lambda item: item["name"])
def test_public_fan3_vectors_qualify_only_after_fresh_15_seconds(
    display_stream, sequence
):
    assert (
        FAN3_PUBLIC_FIXTURE["source"]
        == "synthetic_timing_of_previously_public_wire_frames"
    )
    display, feed, _ = display_stream
    first_heating = None
    for item in sequence["frames"]:
        now = item["elapsed_ms"] / 1000
        feed(bytes.fromhex(item["hex"]), now)
        if item["elapsed_ms"] < sequence["first_heating_ms"]:
            assert display.value(now) is None
        else:
            assert display.value(now) == "heating"
            if first_heating is None:
                first_heating = item["elapsed_ms"]
    assert first_heating == sequence["first_heating_ms"]
    assert first_heating >= 15000
    assert display.expires_at is not None
    assert display.value(display.expires_at - 0.001) == "heating"
    assert display.value(display.expires_at + 0.001) is None


@pytest.mark.parametrize("frame", tuple(dict.fromkeys(SOURCES + FAN3_SOURCES)))
def test_recorded_sources_at_every_stream_split(frame):
    expected = Decoder().feed(frame)
    for split in range(len(frame) + 1):
        observed = []
        decoder = Decoder(
            lambda source, readings, observed=observed: observed.append(
                (source, readings)
            )
        )
        assert decoder.feed(frame[:split]) + decoder.feed(frame[split:]) == expected
        assert len(observed) == 1
        assert observed[0][1] == expected


def test_observer_preserves_typed_output_and_rejection_statistics():
    unknown_mode = checked(MODE[:8] + b"\xff\xff")
    invalid_rpm = checked(RPM[:8] + struct.pack("<f", float("nan")))
    stream = ALL + unknown_mode + invalid_rpm + MODE
    observed = []
    ordinary = Decoder()
    observed_decoder = Decoder(
        lambda source, readings: observed.append((source, readings))
    )
    assert observed_decoder.feed(stream) == ordinary.feed(stream)
    assert asdict(observed_decoder.stats) == asdict(ordinary.stats)
    assert ordinary.stats.value_rejected == 1
    assert observed[-3] == ("operating_mode", [])
    assert [item.key for item in observed[-2][1]] == ["raw_051c"]
    assert observed[-1][0] == "operating_mode"


def test_property_reads_and_unrelated_frames_cannot_qualify(
    display_stream, heating_sources
):
    display, feed, _ = display_stream
    all_sources = b"".join(heating_sources)
    for now in (0, 5, 10, 14):
        feed(all_sources, now)
    for now in (14.5, 15, 15.5):
        assert display.value(now) is None
    feed(bytes.fromhex("118000e1000000040300dba6"), 16)
    assert display.value(16) is None
    feed(heating_sources[3], 16)
    assert display.value(16) == "heating"


@pytest.mark.parametrize("missing", range(4))
def test_missing_or_stale_source_never_qualifies(
    display_stream, heating_sources, missing
):
    display, feed, _ = display_stream
    for now in (0, 5, 10, 15, 20, 25):
        for index, frame in enumerate(heating_sources):
            if index != missing or now == 0:
                feed(frame, now)
        assert display.value(now) is None


def test_expired_gap_cannot_be_bridged_by_new_complete_batch(
    display_stream, heating_sources
):
    display, feed, _ = display_stream
    all_sources = b"".join(heating_sources)
    stabilize(feed, sources=heating_sources)
    assert display.value(21) == "heating"
    assert display.value(21.001) is None
    # No expiry callback or property mutation is needed to detect the gap.
    for now in (22, 27, 32):
        feed(all_sources, now)
        assert display.value(now) is None
    feed(all_sources, 37)
    assert display.value(37) == "heating"
    assert display.expire(43.001)
    assert not display.expire(43.002)
    feed(all_sources, 44)
    assert display.value(44) is None


def test_future_receipts_and_incoherent_sources_fail_closed(
    display_stream, heating_sources
):
    display, feed, _ = display_stream
    all_sources = b"".join(heating_sources)
    mode = heating_sources[0]
    stabilize(feed, sources=heating_sources)
    assert display.value(14.999) is None
    feed(mode, 14.999)
    assert display.value(15) is None
    display.reset()
    for at, frame in zip((20, 26.1, 26.2, 26.3), heating_sources, strict=True):
        feed(frame, at)
    assert display.value(26.3) is None
    # Bringing the oldest source into the coherent interval starts a new window.
    feed(mode, 26.4)
    assert display.value(26.4) is None
    for now in (31.4, 36.4, 41.4):
        feed(all_sources, now)
    assert display.value(41.4) == "heating"


@pytest.mark.parametrize(
    "frame",
    (
        STOPPED,
        checked(RPM[:8] + struct.pack("<f", float("nan"))),
        checked(RPM[:8] + struct.pack("<f", float("inf"))),
        checked(RPM[:8] + struct.pack("<f", -1.0)),
        checked(RPM[:8] + struct.pack("<f", 10001.0)),
        checked(MODE[:8] + b"\xff\xff"),
        checked(MODE[:8] + b"\x01\x00"),
        checked(STATUS[:8] + b"\xff\xff\xff\xff"),
        A7,
        STATUS_9200131A,
        STATUS_8200111A,
    ),
)
def test_changed_or_rejected_source_immediately_clears_indication(
    display_stream, heating_sources, frame
):
    display, feed, _ = display_stream
    all_sources = b"".join(heating_sources)
    stabilize(feed, sources=heating_sources)
    assert display.value(15) == "heating"
    feed(frame, 16)
    assert display.value(16) is None
    for now in (17, 22, 27):
        feed(all_sources, now)
        assert display.value(now) is None
    feed(all_sources, 32)
    assert display.value(32) == "heating"


@pytest.mark.parametrize("valves", (VALVES, A7))
def test_9200131a_context_remains_unavailable_with_either_valve_word(
    display_stream, heating_sources, valves
):
    display, feed, _ = display_stream
    mode, _, _, rpm = heating_sources
    for now in (0, 5, 10, 15, 20):
        feed(mode + STATUS_9200131A + valves + rpm, now)
        assert display.value(now) is None


@pytest.mark.parametrize(
    "before,after",
    ((SOURCES, FAN3_SOURCES), (FAN3_SOURCES, SOURCES)),
    ids=("fan-level-2-to-3", "fan-level-3-to-2"),
)
def test_switching_allowed_full_context_restarts_15_second_proof(
    display_stream, before, after
):
    display, feed, _ = display_stream
    stabilize(feed, sources=before)
    assert display.value(15) == "heating"
    all_sources = b"".join(after)
    for now in (16, 21, 26, 30.999):
        feed(all_sources, now)
        assert display.value(now) is None
    feed(all_sources, 31)
    assert display.value(31) == "heating"


def test_neighboring_full_word_stays_unknown_despite_fan_level_three_mapping(
    display_stream, heating_sources
):
    display, feed, _ = display_stream
    mode, _, valves, rpm = heating_sources
    readings = Decoder().feed(STATUS_8200111A)
    assert {item.key: item.value for item in readings}["controller_fan_level"] == 3
    for now in (0, 5, 10, 15, 20):
        feed(mode + STATUS_8200111A + valves + rpm, now)
        assert display.value(now) is None


def test_invalid_then_valid_mode_in_one_chunk_restarts_proof(
    display_stream, heating_sources
):
    display, feed, _ = display_stream
    all_sources = b"".join(heating_sources)
    mode, status, valves, rpm = heating_sources
    stabilize(feed, sources=heating_sources)
    unknown = checked(mode[:8] + b"\xff\xff")
    feed(mode + unknown + all_sources, 16)
    assert display.value(16) is None
    for now in (21, 26):
        feed(all_sources, now)
        assert display.value(now) is None
    feed(all_sources, 31)
    assert display.value(31) == "heating"
    feed(all_sources + unknown, 32)
    assert display.value(32) is None
    # A new status/valve/RPM receipt cannot resurrect the rejected mode.
    feed(status + valves + rpm, 33)
    assert display.value(33) is None


@pytest.mark.parametrize("source_index", range(4))
@pytest.mark.parametrize("damage", ("checksum", "identity", "reserved", "length"))
def test_bad_frames_cannot_refresh_or_extend_source(
    display_stream, heating_sources, source_index, damage
):
    display, feed, decoder = display_stream
    stabilize(feed, sources=heating_sources)
    frame = heating_sources[source_index]
    body = bytearray(frame[:-2])
    if damage == "checksum":
        bad = frame[:-1] + bytes([frame[-1] ^ 1])
    else:
        index, value = {
            "identity": (2, 7),
            "reserved": (5, 1),
            "length": (7, 0),
        }[damage]
        body[index] = value
        bad = checked(body)
    accepted = decoder.stats.accepted
    feed(bad, 20)
    assert decoder.stats.accepted == accepted
    for index, other in enumerate(heating_sources):
        if index != source_index:
            feed(other, 20)
    assert display.value(21) == "heating"
    assert display.value(21.001) is None


async def test_ha_defaults_identity_availability_unknown_mode_reload_and_recovery(
    hass, frames, heating_sources
):
    all_sources = b"".join(heating_sources)
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])
    clock = SimpleNamespace(now=100.0)
    reconnected = asyncio.Event()

    @asynccontextmanager
    async def receiver(*args):
        nonlocal reader
        if reader.at_eof():
            reader = asyncio.StreamReader()
            reader.feed_data(frames["0xe1"])
            reconnected.set()
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="bde-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    with (
        patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver),
        patch(
            "custom_components.proxon_hesp.coordinator.time",
            SimpleNamespace(monotonic=lambda: clock.now),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, "bde-unit_bde_operating_display"
        )
        registered = registry.async_get(entity_id)
        assert registered.disabled_by == er.RegistryEntryDisabler.INTEGRATION
        assert registered.entity_category.value == "diagnostic"
        assert hass.states.get(entity_id) is None
        fan_id = registry.async_get_entity_id("sensor", DOMAIN, "bde-unit_fan_level")
        assert registered.device_id == registry.async_get(fan_id).device_id
        registry.async_update_entity(entity_id, disabled_by=None, name="My BDE display")
        reader.feed_data(frames["0xe1"])
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        probe = ProxonSensor(
            entry, next(d for d in DESCRIPTIONS if d.key == "bde_operating_display")
        )
        assert hass.states.get(entity_id).state == "unavailable"

        async def receive_at(data, now):
            clock.now = now
            reader.feed_data(data)
            await hass.async_block_till_done()

        for now in (100, 105, 110):
            await receive_at(all_sources, now)
            assert hass.states.get(entity_id).state == "unavailable"
        await receive_at(all_sources, 115)
        state = hass.states.get(entity_id)
        assert state.state == "heating"
        assert state.attributes["device_class"] == "enum"
        assert state.attributes["options"] == ["heating"]
        assert "state_class" not in state.attributes
        assert "unit_of_measurement" not in state.attributes
        clock.now = 121.001
        assert not probe.available
        assert probe.native_value is None
        for now in (122, 127, 132, 137):
            await receive_at(all_sources, now)
            if now == 122:
                assert hass.states.get(entity_id).state == "unavailable"
        assert hass.states.get(entity_id).state == "heating"
        # A rejected-mode-only chunk yields no typed readings, yet must notify HA.
        rejected = runtime.decoder.stats.value_rejected
        await receive_at(checked(heating_sources[0][:8] + b"\xff\xff"), 138)
        assert runtime.decoder.stats.value_rejected == rejected + 1
        assert hass.states.get(entity_id).state == "unavailable"
        for now in (139, 144, 149, 154):
            await receive_at(all_sources, now)
        assert hass.states.get(entity_id).state == "heating"
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        reader.feed_data(frames["0xe1"])
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data is not runtime
        assert runtime.bde_display.value(clock.now) is None
        assert runtime.task is None and runtime.timer is None
        assert registry.async_get(entity_id).name == "My BDE display"
        assert registry.async_get(entity_id).disabled_by is None
        assert hass.states.get(entity_id).state == "unavailable"
        for now in (160, 165, 170, 175):
            await receive_at(all_sources, now)
        assert hass.states.get(entity_id).state == "heating"
        reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "unavailable"
        assert entry.runtime_data.bde_display.value(clock.now) is None
        await asyncio.wait_for(reconnected.wait(), 5)
        await hass.async_block_till_done()
        assert entry.runtime_data.connected
        assert entry.runtime_data.reconnects == 1
        assert hass.states.get(entity_id).state == "unavailable"
        for now in (180, 185, 190):
            await receive_at(all_sources, now)
            assert hass.states.get(entity_id).state == "unavailable"
        await receive_at(all_sources, 195)
        assert hass.states.get(entity_id).state == "heating"
        # Expired state must also notify when the next chunk is rejected-only.
        await receive_at(checked(heating_sources[0][:8] + b"\xff\xff"), 202.001)
        assert hass.states.get(entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_silent_stream_publishes_unavailable_at_scheduled_source_deadline(
    hass, frames, heating_sources
):
    """Drive the real event-loop timer, including a refreshed earliest deadline."""
    all_sources = b"".join(heating_sources)
    loop = asyncio.get_running_loop()
    clock = SimpleNamespace(now=loop.time())
    start = clock.now
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])

    @asynccontextmanager
    async def receiver(*args):
        yield reader

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="bde-expiry-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registered = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "bde-expiry-unit_bde_operating_display",
        config_entry=entry,
        disabled_by=None,
    )
    with (
        patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver),
        patch(
            "custom_components.proxon_hesp.coordinator.time",
            SimpleNamespace(monotonic=lambda: clock.now),
        ),
        patch.object(loop, "time", lambda: clock.now),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        diagnostics_updates = []
        runtime.listen_diagnostics(lambda: diagnostics_updates.append(clock.now))

        def assert_one_expiry_timer():
            active = [
                handle
                for handle in get_scheduled_timer_handles(loop)
                if not handle.cancelled()
                and getattr(handle, "_callback", None) == runtime._expire
            ]
            assert active == [runtime.timer]

        async def advance_to(elapsed):
            clock.now = start + elapsed
            # Advancing loop.time makes its actual TimerHandle due. Do not call
            # the expiry callback or force an entity state write in this test.
            await asyncio.sleep(0)
            await hass.async_block_till_done()

        async def receive_at(data, elapsed):
            await advance_to(elapsed)
            reader.feed_data(data)
            await hass.async_block_till_done()

        for elapsed in (0, 5, 10, 15):
            await receive_at(all_sources, elapsed)
        assert hass.states.get(registered.entity_id).state == "heating"
        await receive_at(all_sources, 16)
        # Updating only mode cannot extend the older remaining source receipts.
        await receive_at(heating_sources[0], 17)
        assert runtime.bde_display.expires_at == start + 22
        assert_one_expiry_timer()
        await advance_to(20)
        updates_at_general_tick = len(diagnostics_updates)
        assert runtime.timer.when() == pytest.approx(start + 22.001, abs=0.00001)
        await advance_to(21.002)
        assert hass.states.get(registered.entity_id).state == "heating"
        await advance_to(21.999)
        assert hass.states.get(registered.entity_id).state == "heating"
        await advance_to(22.002)
        # The stored HA state changes during a completely silent receive stream.
        assert hass.states.get(registered.entity_id).state == "unavailable"
        assert runtime.bde_display.expires_at is None
        assert_one_expiry_timer()
        assert len(diagnostics_updates) == updates_at_general_tick
        assert runtime.timer.when() == pytest.approx(start + 25, abs=0.00001)
        assert runtime.get("fan_level") is not None
        await advance_to(25)
        assert len(diagnostics_updates) == updates_at_general_tick + 1
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.timer is None
        assert runtime._next_general_expiry is None
