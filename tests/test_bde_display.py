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
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    get_scheduled_timer_handles,
)

from custom_components.proxon_hesp.bde_display import BdeDisplay
from custom_components.proxon_hesp.binary_sensor import (
    async_setup_entry as setup_binary_sensors,
)
from custom_components.proxon_hesp.const import (
    CONF_P2_REFERENCE_DISPLAY,
    DOMAIN,
    PROFILE,
)
from custom_components.proxon_hesp.coordinator import ProxonRuntime
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
# These complete frames are already public in the fan and valve tests.
# Their combination and all timing in the blank tests are synthetic.
BLANK_SOURCES = (
    MODE,
    bytes.fromhex("22400008020000080a100080f28f"),
    bytes.fromhex("2240006c00000008250000000da9"),
    STOPPED,
)
A7 = bytes.fromhex("2240006c00000008a70000004738")
STATUS_9200131A = bytes.fromhex("22400008020000081a130092bd31")
# Only this minimal recorded status frame is new; the other frames and all
# combined replay timing below are synthetic reuse of existing public vectors.
STATUS_82009312 = bytes.fromhex("224000080200000812930082069f")
FAN2_BIT15_SOURCES = (MODE, STATUS_82009312, VALVES, RPM)


def checked(body):
    """Build synthetic wire cases; recorded fixtures keep original checksums."""
    return body + checksum(body).to_bytes(2, "little")


STATUS_8200111A = checked(STATUS[:8] + bytes.fromhex("1a110082"))


@pytest.fixture(
    params=(SOURCES, FAN3_SOURCES, FAN2_BIT15_SOURCES),
    ids=("fan-level-2", "fan-level-3", "fan-level-2-bit15"),
)
def heating_sources(request):
    return request.param


@pytest.fixture(
    params=(
        (SOURCES, "heating"),
        (FAN3_SOURCES, "heating"),
        (FAN2_BIT15_SOURCES, "heating"),
        (BLANK_SOURCES, "blank"),
    ),
    ids=("fan-level-2", "fan-level-3", "fan-level-2-bit15", "blank-field"),
)
def display_context(request):
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
    assert display.value(44.578999) == "heating"
    assert display.value(44.579001) is None


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


@pytest.mark.parametrize(
    "frame",
    tuple(dict.fromkeys(SOURCES + FAN3_SOURCES + FAN2_BIT15_SOURCES + BLANK_SOURCES)),
)
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
    display_stream, display_context
):
    sources, expected_state = display_context
    display, feed, _ = display_stream
    all_sources = b"".join(sources)
    for now in (0, 5, 10, 14):
        feed(all_sources, now)
    for now in (14.5, 15, 15.5):
        assert display.value(now) is None
    feed(bytes.fromhex("118000e1000000040300dba6"), 16)
    assert display.value(16) is None
    feed(sources[3], 16)
    assert display.value(16) == expected_state


@pytest.mark.parametrize("missing", range(4))
def test_missing_or_stale_source_never_qualifies(
    display_stream, display_context, missing
):
    sources, expected_state = display_context
    display, feed, _ = display_stream
    for now in (0, 5, 10, 15, 20, 25):
        for index, frame in enumerate(sources):
            if index != missing or now == 0:
                feed(frame, now)
        assert display.value(now) is None


def test_expired_gap_cannot_be_bridged_by_new_complete_batch(
    display_stream, display_context
):
    sources, expected_state = display_context
    display, feed, _ = display_stream
    all_sources = b"".join(sources)
    stabilize(feed, sources=sources)
    assert display.value(22) == expected_state
    assert display.value(22.001) is None
    # No expiry callback or property mutation is needed to detect the gap.
    for now in (23, 28, 33):
        feed(all_sources, now)
        assert display.value(now) is None
    feed(all_sources, 38)
    assert display.value(38) == expected_state
    assert display.expire(45.001)
    assert not display.expire(45.002)
    feed(all_sources, 46)
    assert display.value(46) is None


def test_repeated_winter_sources_with_bounded_poll_jitter_keep_the_display(
    display_stream, display_context
):
    # Synthetic timing with a measured repeated-mode interval of 6.414 s.
    # The source words reuse the public vectors; no new label is inferred.
    sources, expected_state = display_context
    display, feed, _ = display_stream
    stabilize(feed, sources=sources)
    for at, index in (
        (18.704, 3),
        (20, 0),
        (20.222, 2),
        (20.303, 1),
        (23.604, 3),
    ):
        feed(sources[index], at)
        assert display.value(at) == expected_state
    assert display.value(26.413) == expected_state
    for at, index in ((26.414, 0), (26.493, 2), (26.493, 1), (28.5, 3)):
        feed(sources[index], at)
        assert display.value(at) == expected_state
    assert display.expires_at == pytest.approx(33.414)
    assert display.value(33.414) == expected_state
    assert display.value(33.414001) is None
    assert display.expire(33.414001)
    assert display.expires_at is None
    # An actual outage still loses the proof and needs another full 15 s.
    for at in (34, 39, 44):
        feed(b"".join(sources), at)
        assert display.value(at) is None
    feed(b"".join(sources), 49)
    assert display.value(49) == expected_state


@pytest.mark.parametrize("late_source", range(4))
def test_each_winter_source_has_an_inclusive_seven_second_hard_limit(
    display_stream, display_context, late_source
):
    sources, expected_state = display_context
    display, feed, _ = display_stream
    stabilize(feed, sources=sources)
    for index, source in enumerate(sources):
        if index != late_source:
            feed(source, 20)
    assert display.value(22) == expected_state
    assert display.value(22.000001) is None
    feed(sources[late_source], 22.000001)
    assert display.value(22.000001) is None


def test_winter_and_led_keep_independent_hard_source_deadlines():
    display = BdeDisplay(p2_reference=True, supports_green_led=True)
    clock = SimpleNamespace(now=0.0)
    decoder = Decoder(
        lambda source, readings: display.observe(source, readings, clock.now)
    )
    for clock.now in (0, 5, 10, 15):
        decoder.feed(ALL)
    assert display.value(21.5) == "heating"
    assert display.value(22) == "heating"
    assert display.value(22.000001) is None
    assert display.green_led(23) is True
    assert display.green_led(23.000001) is None
    assert display.expire(23.000001)


def test_future_receipts_and_incoherent_sources_fail_closed(
    display_stream, display_context
):
    sources, expected_state = display_context
    display, feed, _ = display_stream
    all_sources = b"".join(sources)
    mode = sources[0]
    stabilize(feed, sources=sources)
    assert display.value(14.999) is None
    feed(mode, 14.999)
    assert display.value(15) is None
    display.reset()
    for at, frame in zip((20, 27.1, 27.2, 27.3), sources, strict=True):
        feed(frame, at)
    assert display.value(27.3) is None
    # Bringing the oldest source into the coherent interval starts a new window.
    feed(mode, 27.4)
    assert display.value(27.4) is None
    for now in (32.4, 37.4, 42.4):
        feed(all_sources, now)
    assert display.value(42.4) == expected_state


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
    (
        (SOURCES, FAN3_SOURCES),
        (FAN3_SOURCES, SOURCES),
        (SOURCES, BLANK_SOURCES),
        (FAN3_SOURCES, BLANK_SOURCES),
        (BLANK_SOURCES, SOURCES),
        (BLANK_SOURCES, FAN3_SOURCES),
        (SOURCES, FAN2_BIT15_SOURCES),
        (FAN2_BIT15_SOURCES, SOURCES),
        (FAN3_SOURCES, FAN2_BIT15_SOURCES),
        (FAN2_BIT15_SOURCES, FAN3_SOURCES),
        (BLANK_SOURCES, FAN2_BIT15_SOURCES),
        (FAN2_BIT15_SOURCES, BLANK_SOURCES),
    ),
    ids=(
        "fan-level-2-to-3",
        "fan-level-3-to-2",
        "heating-2-to-blank",
        "heating-3-to-blank",
        "blank-to-heating-2",
        "blank-to-heating-3",
        "heating-2-to-bit15",
        "bit15-to-heating-2",
        "heating-3-to-bit15",
        "bit15-to-heating-3",
        "blank-to-bit15",
        "bit15-to-blank",
    ),
)
def test_allowed_context_change_keeps_only_an_already_qualified_same_label(
    display_stream, before, after
):
    display, feed, _ = display_stream
    stabilize(feed, sources=before)
    assert display.value(15) == ("blank" if before == BLANK_SOURCES else "heating")
    all_sources = b"".join(after)
    for now in (16, 21, 26, 30.999):
        feed(all_sources, now)
        assert display.value(now) == (
            "heating" if before != BLANK_SOURCES and after != BLANK_SOURCES else None
        )
    feed(all_sources, 31)
    assert display.value(31) == ("blank" if after == BLANK_SOURCES else "heating")


def test_unqualified_heating_context_change_still_requires_full_stability(
    display_stream,
):
    display, feed, _ = display_stream
    for at in (0, 5, 10):
        feed(ALL, at)
    for at in (14, 19, 24, 28.999):
        feed(b"".join(FAN3_SOURCES), at)
        assert display.value(at) is None
    assert display.value(29) is None
    feed(RPM, 29)
    assert display.value(29) == "heating"


def test_unknown_between_known_heating_contexts_cannot_keep_the_old_label(
    display_stream,
):
    display, feed, _ = display_stream
    stabilize(feed)
    feed(STATUS_8200111A, 16)
    assert display.value(16) is None
    for at in (16.1, 21.1, 26.1, 31.099):
        feed(b"".join(FAN3_SOURCES), at)
        assert display.value(at) is None
    feed(RPM, 31.1)
    assert display.value(31.1) == "heating"


@pytest.mark.parametrize(
    ("status_word", "valve_word"),
    (
        (0x8200931A, 0x27),
        (0x9200931A, 0x27),
        (0x9200931A, 0xA7),
        (0x92009312, 0x27),
        (0x92009312, 0xA7),
        (0x92001312, 0xA7),
        (0x92001312, 0x27),
        (0x9200131A, 0x27),
    ),
)
def test_unsupported_winter_words_stay_unknown_with_a_running_compressor(
    display_stream, status_word, valve_word
):
    # Synthetic negative combinations, not additional display references.
    display, feed, _ = display_stream
    status = checked(STATUS[:8] + status_word.to_bytes(4, "little"))
    valves = checked(VALVES[:8] + valve_word.to_bytes(4, "little"))
    stabilize(feed)
    for at in (16, 21, 26, 31, 36):
        feed(MODE + status + valves + RPM, at)
        assert display.value(at) is None


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


@pytest.mark.parametrize("mode", (0, 1, 3, 4))
@pytest.mark.parametrize("valves", (VALVES, A7))
def test_new_level_two_word_does_not_infer_heating_outside_eco_winter(
    display_stream, mode, valves
):
    display, feed, _ = display_stream
    other_mode = checked(MODE[:8] + mode.to_bytes(2, "little"))
    stream = other_mode + STATUS_82009312 + valves + RPM
    for now in (0, 5, 10, 15, 20):
        readings = feed(stream, now)
        assert [r.value for r in readings if r.key == "controller_fan_level"] == [2]
        assert display.value(now) is None


@pytest.mark.parametrize("valves", (VALVES, A7, BLANK_SOURCES[2]))
def test_new_level_two_word_with_zero_speed_is_neither_heating_nor_blank(
    display_stream, valves
):
    display, feed, _ = display_stream
    stream = MODE + STATUS_82009312 + valves + STOPPED
    for now in (0, 5, 10, 15, 20):
        feed(stream, now)
        assert display.value(now) is None


def test_new_level_two_word_before_compressor_start_needs_new_15_second_proof(
    display_stream,
):
    display, feed, _ = display_stream
    stopped = MODE + STATUS_82009312 + VALVES + STOPPED
    for now in (0, 5, 10, 15, 20):
        feed(stopped, now)
        assert display.value(now) is None
    feed(RPM, 21)
    running = b"".join(FAN2_BIT15_SOURCES)
    for now in (26, 31, 35.999):
        feed(running, now)
        assert display.value(now) is None
    assert display.value(36) is None
    feed(RPM, 36)
    assert display.value(36) == "heating"


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
    display_stream, display_context, source_index, damage
):
    sources, expected_state = display_context
    display, feed, decoder = display_stream
    stabilize(feed, sources=sources)
    frame = sources[source_index]
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
    for index, other in enumerate(sources):
        if index != source_index:
            feed(other, 20)
    assert display.value(22) == expected_state
    assert display.value(22.001) is None


async def test_ha_defaults_identity_availability_unknown_mode_reload_and_recovery(
    hass, frames, display_context
):
    sources, expected_state = display_context
    all_sources = b"".join(sources)
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
        assert state.state == expected_state
        assert state.attributes["device_class"] == "enum"
        assert state.attributes["options"] == ["heating", "blank", "cooling"]
        assert "state_class" not in state.attributes
        assert "unit_of_measurement" not in state.attributes
        clock.now = 122.001
        assert not probe.available
        assert probe.native_value is None
        for now in (123, 128, 133, 138):
            await receive_at(all_sources, now)
            if now == 123:
                assert hass.states.get(entity_id).state == "unavailable"
        assert hass.states.get(entity_id).state == expected_state
        # A rejected-mode-only chunk yields no typed readings, yet must notify HA.
        rejected = runtime.decoder.stats.value_rejected
        await receive_at(checked(sources[0][:8] + b"\xff\xff"), 138)
        assert runtime.decoder.stats.value_rejected == rejected + 1
        assert hass.states.get(entity_id).state == "unavailable"
        for now in (139, 144, 149, 154):
            await receive_at(all_sources, now)
        assert hass.states.get(entity_id).state == expected_state
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
        assert hass.states.get(entity_id).state == expected_state
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
        assert hass.states.get(entity_id).state == expected_state
        # Both directions use the same entity and require a new 15-second proof.
        other_sources = SOURCES if expected_state == "blank" else BLANK_SOURCES
        other_state = "heating" if expected_state == "blank" else "blank"
        for now in (196, 201, 206):
            await receive_at(b"".join(other_sources), now)
            assert hass.states.get(entity_id).state == "unavailable"
        await receive_at(b"".join(other_sources), 211)
        assert hass.states.get(entity_id).state == other_state
        for now in (212, 217, 222):
            await receive_at(all_sources, now)
            assert hass.states.get(entity_id).state == "unavailable"
        await receive_at(all_sources, 227)
        assert hass.states.get(entity_id).state == expected_state
        assert (
            registry.async_get_entity_id(
                "sensor", DOMAIN, "bde-unit_bde_operating_display"
            )
            == entity_id
        )
        assert registry.async_get(entity_id).name == "My BDE display"
        # Expired state must also notify when the next chunk is rejected-only.
        await receive_at(checked(sources[0][:8] + b"\xff\xff"), 234.001)
        assert hass.states.get(entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_silent_stream_publishes_unavailable_at_scheduled_source_deadline(
    hass, frames, display_context
):
    """Drive the real event-loop timer, including a refreshed earliest deadline."""
    sources, expected_state = display_context
    all_sources = b"".join(sources)
    loop = asyncio.get_running_loop()
    # An integral origin keeps the exact 15-second boundary representable.
    clock = SimpleNamespace(now=float(int(loop.time())))
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
        assert hass.states.get(registered.entity_id).state == expected_state
        await receive_at(all_sources, 16)
        # Updating only mode cannot extend the older remaining source receipts.
        await receive_at(sources[0], 17)
        assert runtime.bde_display.expires_at == start + 23
        assert_one_expiry_timer()
        await advance_to(20)
        updates_at_general_tick = len(diagnostics_updates)
        assert runtime.timer.when() == pytest.approx(start + 23.001, abs=0.00001)
        await advance_to(21.002)
        assert hass.states.get(registered.entity_id).state == expected_state
        await advance_to(22.999)
        assert hass.states.get(registered.entity_id).state == expected_state
        await advance_to(23.002)
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


async def test_upper_green_led_uses_fresh_validated_pairs(hass, frames):
    # All positive frames were published for the operating mode, fan, or RPM.
    # This combined playback and its reception timing are synthetic.
    comfort = bytes.fromhex("1180000a020000040300caef")
    dark = BLANK_SOURCES[1]
    comfort_lit = bytes.fromhex("22400008020000081a130080d98b")
    invalid_mode = checked(MODE[:8] + b"\xff\xff")
    corrupt_comfort = comfort[:-1] + bytes([comfort[-1] ^ 1])
    wrong_status_node = checked(b"\x11\x80\x00" + dark[3:-2])

    loop = asyncio.get_running_loop()
    start = float(int(loop.time()))
    clock = SimpleNamespace(now=start)
    first_reader, next_reader = asyncio.StreamReader(), asyncio.StreamReader()
    first_reader.feed_data(frames["0xe1"])
    readers = iter((first_reader, next_reader))

    @asynccontextmanager
    async def receiver(*args):
        yield next(readers)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="led-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    registered = er.async_get(hass).async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "led-unit_bde_green_led",
        config_entry=entry,
        disabled_by=None,
    )

    async def advance_to(elapsed):
        clock.now = start + elapsed
        await asyncio.sleep(0)
        await hass.async_block_till_done()

    async def receive_at(elapsed, data, expected, reader=first_reader):
        await advance_to(elapsed)
        reader.feed_data(data)
        await hass.async_block_till_done()
        assert hass.states.is_state(registered.entity_id, expected)

    async def set_reference(enabled):
        form = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            form["flow_id"], {CONF_P2_REFERENCE_DISPLAY: enabled}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

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
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        # A frame pair shared by P2 and FWT is insufficient to select a panel.
        await receive_at(0.25, comfort + comfort_lit + STOPPED, "unavailable")
        await set_reference(True)
        assert entry.runtime_data is runtime
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await receive_at(1, STATUS, "unavailable")
        await receive_at(2, MODE + dark, "off")
        await receive_at(3, FAN3_SOURCES[1], "on")
        await receive_at(3.125, STATUS_9200131A, "unavailable")
        await receive_at(3.25, STATUS_82009312, "unavailable")
        await receive_at(3.5, STATUS, "on")
        await receive_at(3.75, wrong_status_node, "on")
        await receive_at(3.8, RPM, "on")
        await receive_at(3.9, STATUS_9200131A, "on")
        assert hass.states.get(registered.entity_id).attributes["assumed_state"]
        assert (
            hass.states.get(registered.entity_id).attributes["state_basis"]
            == "inferred_continuity"
        )
        await receive_at(3.95, STATUS, "on")
        assert not hass.states.get(registered.entity_id).attributes.get("assumed_state")
        assert (
            hass.states.get(registered.entity_id).attributes["state_basis"]
            == "display_reference"
        )
        await receive_at(4, comfort, "unavailable")
        await receive_at(5, MODE, "unavailable")
        await receive_at(6, dark, "off")
        await receive_at(7, comfort + comfort_lit + STOPPED, "on")
        assert runtime.get_bde_operating_display() is None
        assert runtime.get("compressor_rpm").value == 0
        await receive_at(7.5, FAN3_SOURCES[1], "unavailable")
        await receive_at(8, STATUS, "unavailable")
        await receive_at(9, comfort_lit, "on")
        await receive_at(11, corrupt_comfort, "on")
        await receive_at(12, comfort_lit, "on")
        assert runtime.bde_display.green_led_expires_at == start + 15
        await advance_to(13)
        assert runtime.get_bde_green_led() is True
        await advance_to(15.002)
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await receive_at(16, comfort, "on")
        await advance_to(20.002)
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await receive_at(21, comfort_lit, "on")
        await receive_at(22, invalid_mode, "unavailable")
        await receive_at(23, comfort, "unavailable")
        await receive_at(24, comfort_lit, "on")
        first_reader.feed_eof()
        await hass.async_block_till_done()
        assert not runtime.connected
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await advance_to(25.002)
        # The reconnect coroutine resumes after its sleep's timer callback.
        await asyncio.sleep(0)
        assert runtime.connected
        await receive_at(26, comfort_lit, "unavailable", next_reader)
        await receive_at(27, comfort, "on", next_reader)
        await set_reference(False)
        assert entry.runtime_data is runtime
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await receive_at(28, comfort + comfort_lit, "unavailable", next_reader)
        await receive_at(29, MODE + FAN3_SOURCES[1], "unavailable", next_reader)
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.timer is None


@pytest.fixture
def led_stream():
    display = BdeDisplay(p2_reference=True, supports_green_led=True)
    clock = SimpleNamespace(now=0.0)
    decoder = Decoder(
        lambda source, readings: display.observe(source, readings, clock.now)
    )

    def feed(data, at):
        clock.now = at
        decoder.feed(data)

    return display, feed


LED_BIT28_LEVEL2 = checked(STATUS[:8] + bytes.fromhex("12130092"))
LED_PRESTOP_LEVEL2 = checked(STATUS[:8] + bytes.fromhex("12110082"))
LED_BIT15_LEVEL3 = checked(STATUS[:8] + bytes.fromhex("1a930082"))
ADDITIONAL_LED_STATUSES = (STATUS_82009312, LED_PRESTOP_LEVEL2, LED_BIT15_LEVEL3)


@pytest.mark.parametrize("status", ADDITIONAL_LED_STATUSES)
def test_additional_optical_led_context_requires_all_fresh_sources(led_stream, status):
    display, feed = led_stream
    feed(MODE + status, 0)
    assert display.green_led(0) is None
    feed(RPM, 1)
    assert display.green_led(1) is None
    feed(VALVES, 2)
    assert display.green_led(2) is True
    assert display.green_led_basis(2) == "display_reference"
    assert display.green_led_expires_at == 8
    assert display.green_led(8.000001) is None


@pytest.mark.parametrize("status", ADDITIONAL_LED_STATUSES)
@pytest.mark.parametrize("expired", (MODE, VALVES, RPM, "status"))
def test_additional_optical_led_expires_with_each_required_source(
    led_stream, status, expired
):
    display, feed = led_stream
    sources = (MODE, status, VALVES, RPM)
    feed(b"".join(sources), 0)
    assert display.green_led(0) is True
    omitted = status if expired == "status" else expired
    feed(b"".join(frame for frame in sources if frame != omitted), 7)
    assert display.green_led(8) is True
    assert display.green_led(8.000001) is None
    feed(b"".join(frame for frame in sources if frame != omitted), 8.1)
    assert display.green_led(8.1) is None


@pytest.mark.parametrize("status", ADDITIONAL_LED_STATUSES)
def test_additional_optical_led_rejects_other_valves_and_zero_rpm(led_stream, status):
    display, feed = led_stream
    feed(MODE + status + VALVES + RPM, 0)
    assert display.green_led(0) is True
    feed(A7, 1)
    assert display.green_led(1) is None
    feed(VALVES, 2)
    assert display.green_led(2) is True
    feed(STOPPED, 3)
    assert display.green_led(3) is None
    feed(RPM, 4)
    assert display.green_led(4) is True
    feed(checked(VALVES[:8] + bytes.fromhex("25000000")), 5)
    assert display.green_led(5) is None


@pytest.mark.parametrize("status", ADDITIONAL_LED_STATUSES)
@pytest.mark.parametrize("value", (-1, float("nan"), float("inf"), 10001))
def test_additional_optical_led_rejects_invalid_rpm(led_stream, status, value):
    display, feed = led_stream
    feed(MODE + status + VALVES + RPM, 0)
    assert display.green_led(0) is True
    feed(checked(RPM[:8] + struct.pack("<f", value)), 1)
    assert display.green_led(1) is None
    assert display.green_led_basis(1) is None


@pytest.mark.parametrize("status", ADDITIONAL_LED_STATUSES)
def test_additional_optical_led_does_not_assign_a_bde_label_or_ignore_profile(
    led_stream, status
):
    display, feed = led_stream
    feed(MODE + status + VALVES + RPM, 0)
    assert display.green_led(0) is True
    assert display.value(0) is None
    if status in (LED_PRESTOP_LEVEL2, LED_BIT15_LEVEL3):
        stabilize(feed, sources=(MODE, status, VALVES, RPM))
        assert display.value(15) is None
        assert display.fan_level_confirmed(15) == (status == LED_BIT15_LEVEL3)
    if status == LED_BIT15_LEVEL3:
        assert all(
            reading.key != "controller_fan_level" for reading in Decoder().feed(status)
        )
    display.configure_p2_reference(False)
    feed(MODE + status + VALVES + RPM, 16)
    assert display.green_led(16) is None
    display.configure_p2_reference(True)
    feed(status, 17)
    assert display.green_led(17) is None


@pytest.mark.parametrize("status", ADDITIONAL_LED_STATUSES)
def test_additional_optical_led_does_not_admit_neighboring_status_words(
    led_stream, status
):
    display, feed = led_stream
    feed(MODE + status + VALVES + RPM, 0)
    for bit in (0, 2, 5, 6, 7, 14, 17, 24, 28):
        payload = (int.from_bytes(status[8:-2], "little") ^ (1 << bit)).to_bytes(
            4, "little"
        )
        feed(checked(status[:8] + payload), 1)
        assert display.green_led(1) is None
    feed(MODE + status + VALVES + RPM, 2)
    assert display.green_led(2) is True
    feed(bytes.fromhex("1180000a020000040300caef"), 3)
    assert display.green_led(3) is None


@pytest.mark.parametrize("status", (STATUS_9200131A, LED_BIT28_LEVEL2))
def test_bit28_led_cannot_start_without_an_observed_on_anchor(led_stream, status):
    display, feed = led_stream
    feed(MODE + RPM + status, 0)
    assert display.green_led(0) is None
    assert display.green_led_basis(0) is None
    feed(STATUS, 1)
    assert display.green_led_basis(1) == "display_reference"
    feed(status, 2)
    assert display.green_led(2) is True
    assert display.green_led_basis(2) == "inferred_continuity"


def test_bit28_led_continuity_covers_a_long_fresh_phase(led_stream):
    display, feed = led_stream
    feed(MODE + STATUS + RPM, 0)
    for at in range(5, 406, 5):
        status = STATUS_9200131A if at % 10 else LED_BIT28_LEVEL2
        feed(MODE + RPM + status, at)
        assert display.green_led(at) is True
        assert display.green_led_basis(at) == "inferred_continuity"
        # Neither an inferred LED nor positive RPM assigns a BDE text label.
        assert display.value(at) is None
    feed(STATUS, 406)
    assert display.green_led_basis(406) == "display_reference"


@pytest.mark.parametrize("value", (0, -1, float("nan"), float("inf"), 10001))
def test_bit28_zero_or_invalid_rpm_breaks_continuity(led_stream, value):
    display, feed = led_stream
    feed(MODE + STATUS + RPM, 0)
    feed(STATUS_9200131A, 1)
    invalid = checked(RPM[:8] + struct.pack("<f", value))
    feed(invalid, 2)
    assert display.green_led(2) is None
    feed(RPM + STATUS_9200131A, 3)
    assert display.green_led(3) is None
    feed(STATUS, 4)
    feed(STATUS_9200131A, 5)
    assert display.green_led(5) is True


@pytest.mark.parametrize("source", (MODE, STATUS_9200131A, RPM))
def test_bit28_expired_dependency_cannot_be_revived_by_a_fresh_batch(
    led_stream, source
):
    display, feed = led_stream
    feed(MODE + STATUS + RPM + STATUS_9200131A, 0)
    for frame in (MODE, STATUS_9200131A, RPM):
        if frame != source:
            feed(frame, 7)
    assert display.green_led(8) is True
    assert display.green_led(8.000001) is None
    feed(MODE + RPM + STATUS_9200131A, 8.000001)
    assert display.green_led(8.000001) is None
    assert display.green_led_basis(8.000001) is None


@pytest.mark.parametrize(
    "interruption",
    (
        STATUS_82009312,
        BLANK_SOURCES[1],
        checked(MODE[:8] + b"\xff\xff"),
        bytes.fromhex("1180000a020000040300caef"),
    ),
)
def test_bit28_unknown_off_and_mode_changes_break_the_anchor(led_stream, interruption):
    display, feed = led_stream
    feed(MODE + STATUS + RPM, 0)
    feed(STATUS_9200131A, 1)
    feed(interruption, 2)
    feed(MODE + RPM + STATUS_9200131A, 3)
    assert display.green_led(3) is None


def test_bit28_reset_and_variant_change_forget_the_anchor(led_stream):
    display, feed = led_stream
    for at in (0, 10):
        feed(MODE + STATUS + RPM + STATUS_9200131A, at)
        assert display.green_led(at) is True
        if at == 0:
            display.reset()
        else:
            display.configure_p2_reference(False)
            display.configure_p2_reference(True)
        feed(MODE + RPM + STATUS_9200131A, at + 1)
        assert display.green_led(at + 1) is None


@pytest.mark.parametrize("last_gap", (6.980, 7.479))
def test_led_eight_second_limit_covers_observed_unchanged_poll_intervals(
    led_stream, last_gap
):
    display, feed = led_stream
    feed(MODE + STATUS, 0)
    feed(MODE + STATUS, last_gap)
    assert display.green_led(last_gap) is True
    assert display.green_led_basis(last_gap) == "display_reference"
    assert display.green_led(last_gap + 8) is True
    assert display.green_led(last_gap + 8.000001) is None
    display.expire(last_gap + 8.000001)
    assert display.green_led_basis(last_gap + 8.000001) is None


@pytest.mark.parametrize("status", (STATUS_9200131A, LED_BIT15_LEVEL3))
async def test_p2_fan_level_requires_fresh_preceding_eco_winter(hass, frames, status):
    comfort = bytes.fromhex("1180000a020000040300caef")
    adjacent = checked(STATUS[:8] + bytes.fromhex("12130092"))
    corrupted = status[:-1] + bytes([status[-1] ^ 1])
    loop = asyncio.get_running_loop()
    start = float(int(loop.time()))
    clock = SimpleNamespace(now=start)
    first_reader, next_reader = asyncio.StreamReader(), asyncio.StreamReader()
    first_reader.feed_data(frames["0xe1"])
    readers = iter((first_reader, next_reader))

    @asynccontextmanager
    async def receiver(*args):
        yield next(readers)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="context-fan-unit",
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
        options={CONF_P2_REFERENCE_DISPLAY: True},
    )
    entry.add_to_hass(hass)
    registered = er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "context-fan-unit_controller_fan_level",
        config_entry=entry,
        disabled_by=None,
    )

    async def advance_to(elapsed):
        clock.now = start + elapsed
        await asyncio.sleep(0)
        await hass.async_block_till_done()

    async def receive_at(elapsed, data, expected, reader=first_reader):
        await advance_to(elapsed)
        reader.feed_data(data)
        await hass.async_block_till_done()
        assert hass.states.is_state(registered.entity_id, expected)

    with (
        patch("custom_components.proxon_hesp.coordinator.open_receiver", receiver),
        patch(
            "custom_components.proxon_hesp.coordinator.time",
            SimpleNamespace(monotonic=lambda: clock.now),
        ),
        patch.object(loop, "time", lambda: clock.now),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await receive_at(1, status + MODE, "unavailable")
        await receive_at(2, corrupted, "unavailable")
        await receive_at(3, status, "3")
        runtime = entry.runtime_data
        assert runtime.get_bde_operating_display() is None
        assert runtime.get_bde_green_led() is None
        await receive_at(4.25, comfort + MODE, "unavailable")
        await receive_at(5, status, "3")
        await receive_at(6, adjacent, "unavailable")
        await receive_at(7, status, "3")
        await advance_to(10)  # Earlier general maintenance tick.
        assert runtime.timer.when() == pytest.approx(start + 10.251, abs=0.00001)
        await advance_to(10.252)
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await receive_at(11, status + MODE, "unavailable")
        await receive_at(12, status, "3")
        await receive_at(13, MODE + STATUS, "2")
        await receive_at(14, comfort + STATUS, "2")
        await receive_at(15, status, "unavailable")
        await receive_at(16, MODE + status, "3")
        first_reader.feed_eof()
        await hass.async_block_till_done()
        assert hass.states.is_state(registered.entity_id, "unavailable")
        await advance_to(17.002)
        await asyncio.sleep(0)
        await receive_at(18, status + MODE, "unavailable", next_reader)
        await receive_at(19, status, "3", next_reader)
        runtime.capture.start()
        await receive_at(20, status, "3", next_reader)
        capture_state = runtime.capture.started, runtime.capture.size

        async def set_variant(enabled):
            form = await hass.config_entries.options.async_init(entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                form["flow_id"], {CONF_P2_REFERENCE_DISPLAY: enabled}
            )
            assert result["type"] is FlowResultType.CREATE_ENTRY
            await hass.async_block_till_done()
            assert entry.runtime_data is runtime
            assert runtime.capture.reason == "recording"
            assert (runtime.capture.started, runtime.capture.size) == capture_state
            assert hass.states.is_state(registered.entity_id, "unavailable")

        await set_variant(False)
        await receive_at(21, MODE + status, "unavailable", next_reader)
        capture_state = runtime.capture.started, runtime.capture.size
        await set_variant(True)
        await receive_at(22, status + MODE, "unavailable", next_reader)
        await receive_at(23, status, "3", next_reader)
        assert runtime.diagnostics()["application_bytes_sent"] == 0
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("status", (STATUS_9200131A, LED_BIT15_LEVEL3))
async def test_p2_fan_level_requires_the_observed_transport_profile(hass, status):
    runtime = ProxonRuntime(
        hass, "gateway.test", 4196, profile="other", p2_reference_display=True
    )
    runtime.connected = True
    readings = runtime.decoder.feed(MODE + status)
    assert all(reading.key != "controller_fan_level" for reading in readings)
    for reading in readings:
        runtime.values[reading.key] = (reading, asyncio.get_running_loop().time())
    assert runtime.bde_display.fan_level_expires_at is None
    assert runtime.get("controller_fan_level") is None


async def test_upper_green_led_is_inactive_for_other_profiles(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="PROXON", unique_id="other-unit")
    runtime = entry.runtime_data = ProxonRuntime(
        hass, "gateway.test", 4196, profile="other"
    )
    runtime.connected = True
    runtime.decoder.feed(MODE + STATUS)
    assert runtime.get_bde_green_led() is None
    assert runtime.bde_display.green_led_expires_at is None
    entities = []
    await setup_binary_sensors(hass, entry, entities.extend)
    assert all(entity.entity_description.key != "bde_green_led" for entity in entities)


def test_blank_qualifies_only_on_actual_receipt_at_the_stability_boundary(
    display_stream,
):
    display, feed, _ = display_stream
    for now in (0, 5, 10, 14.999):
        feed(b"".join(BLANK_SOURCES), now)
        assert display.value(now) is None
    assert display.value(15) is None
    feed(BLANK_SOURCES[3], 15)
    assert display.value(15) == "blank"
    assert display.expires_at == pytest.approx(21.999)


@pytest.mark.parametrize(
    "rpm",
    (
        2**-149,
        1e-12,
        1.0,
        2700.0,
        -(2**-149),
        -1.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        10001.0,
    ),
)
def test_blank_rejects_nonzero_or_invalid_rpm_and_restarts_proof(display_stream, rpm):
    display, feed, _ = display_stream
    stabilize(feed, sources=BLANK_SOURCES)
    assert display.value(15) == "blank"
    feed(checked(STOPPED[:8] + struct.pack("<f", rpm)), 16)
    assert display.value(16) is None
    for now in (17, 22, 27):
        feed(b"".join(BLANK_SOURCES), now)
        assert display.value(now) is None
    feed(b"".join(BLANK_SOURCES), 32)
    assert display.value(32) == "blank"


@pytest.mark.parametrize("mode", (0, 1, 3, 4, 0xFFFF))
def test_blank_is_not_inferred_in_other_or_rejected_modes(display_stream, mode):
    display, feed, _ = display_stream
    sources = (checked(MODE[:8] + mode.to_bytes(2, "little")), *BLANK_SOURCES[1:])
    for now in (0, 5, 10, 15, 20):
        feed(b"".join(sources), now)
        assert display.value(now) is None


def test_blank_requires_both_complete_words_without_ignored_bits(display_stream):
    display, feed, _ = display_stream
    for index, word in ((1, 0x8000100A), (2, 0x25)):
        for bit in range(32):
            display.reset()
            sources = list(BLANK_SOURCES)
            sources[index] = checked(
                sources[index][:8] + (word ^ (1 << bit)).to_bytes(4, "little")
            )
            for now in (0, 5, 10, 15, 20):
                feed(b"".join(sources), now)
                assert display.value(now) is None, (index, bit)


def test_display_enum_has_specific_labels_in_both_languages():
    folder = Path(__file__).parents[1] / "custom_components/proxon_hesp"
    for name, label, cooling in (
        ("strings.json", "Blank operating field", "Cooling"),
        ("translations/en.json", "Blank operating field", "Cooling"),
        ("translations/de.json", "Betriebsfeld leer", "Kühlbetrieb"),
    ):
        states = json.loads((folder / name).read_text())["entity"]["sensor"][
            "bde_operating_display"
        ]["state"]
        assert states["blank"] == label
        assert states["cooling"] == cooling
        assert set(states) == {"heating", "blank", "cooling"}
