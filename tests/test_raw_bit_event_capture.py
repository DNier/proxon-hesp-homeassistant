"""Undecoded candidate edges retain bounded photo windows without device writes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import CONF_EVENT_CAPTURE, DOMAIN, PROFILE
from custom_components.proxon_hesp.event_capture import EventCapture
from custom_components.proxon_hesp.hesp.checksum import checksum

# Synthetic sources and payloads test wire identity, never an actuator meaning.
SOURCES = (
    ("raw_118000_01f8", "118000", 0x01F8, 4, 11),
    ("raw_118000_03b6", "118000", 0x03B6, 4, 1),
    ("raw_118007_0191", "118007", 0x0191, 2, 1),
)


def raw_value(source, active, other_bits=0):
    _, _, _, size, bit = source
    return (other_bits | (int(active) << bit)).to_bytes(size, "little").hex()


def source_frame(source, active, other_bits=0):
    _, identity, dp, size, _ = source
    body = (
        bytes.fromhex(identity)
        + dp.to_bytes(2, "little")
        + b"\x00\x00"
        + bytes([size * 2])
        + bytes.fromhex(raw_value(source, active, other_bits))
    )
    return checked(body)


def checked(body):
    return body + checksum(body).to_bytes(2, "little")


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source[0])
async def test_only_the_reviewed_bit_changes_and_preserves_full_raw_payload(source):
    event = EventCapture(True)
    key, _, _, _, bit = source
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        event.feed(b"before")
        event.observe_raw_bit(key, raw_value(source, False))
        event.observe_raw_bit(key, raw_value(source, False, 1))
        assert not event.events
        assert event.capture.timer is None
        clock.return_value = 110
        event.feed(b"edge")
        event.observe_raw_bit(key, raw_value(source, True, 1))
        timer = event.capture.timer
        assert event.events == [
            {
                "elapsed_ms": 10000,
                "type": "raw_bit_changed",
                "key": key,
                "bit": bit,
                "active": True,
                "raw": raw_value(source, True, 1),
            }
        ]
        assert event.capture.recording_duration == 610
        assert timer.when() == 710
        assert event.summary()["requested_post_seconds"] == 600
        clock.return_value = 111
        event.observe_raw_bit(key, raw_value(source, True, 0x10))
        event.observe_raw_bit("raw_006c", "ffffffff")
        event.observe_raw_bit("raw_0208", "ffffffff")
        event.observe_raw_bit("raw_118000_0191", "ffff")
        assert len(event.events) == 1
        assert event.capture.timer is timer
        clock.return_value = 112
        event.feed(b"falling")
        event.observe_raw_bit(key, raw_value(source, False, 0x10))
        assert event.events[-1]["active"] is False
        assert event.events[-1]["raw"] == raw_value(source, False, 0x10)
        assert timer.cancelled()
        assert event.capture.timer.when() == 712
    event.clear()


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source[0])
@pytest.mark.parametrize("gap,expected_count", [(29.999, 1), (30, 0)])
async def test_each_source_requires_a_fresh_baseline(source, gap, expected_count):
    event = EventCapture(True)
    key = source[0]
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        event.observe_raw_bit(key, raw_value(source, False))
        clock.return_value += gap
        event.feed(b"received")
        event.observe_raw_bit(key, raw_value(source, True))
        assert len(event.events) == expected_count
        if not expected_count:
            # A stale sample establishes the next baseline, not a permanent gap.
            clock.return_value += 1
            event.observe_raw_bit(key, raw_value(source, False))
            assert len(event.events) == 1
            assert event.events[0]["active"] is False
    event.clear()


@pytest.mark.parametrize("reset", ["clear", "disconnect", "disable"])
async def test_opt_in_and_resets_never_replay_a_candidate_edge(reset):
    source = SOURCES[0]
    key = source[0]
    event = EventCapture()
    event.feed(b"disabled")
    event.observe_raw_bit(key, raw_value(source, False))
    assert not event.ring and not event.raw_bit_baselines
    event.configure(True)
    event.feed(b"baseline")
    event.observe_raw_bit(key, raw_value(source, False))
    event.observe_raw_bit(key, raw_value(source, True))
    timer = event.capture.timer
    assert len(event.events) == 1
    if reset == "disable":
        event.configure(False)
        event.observe_raw_bit(key, raw_value(source, False))
        event.configure(True)
    else:
        getattr(event, reset)()
    assert timer.cancelled()
    assert not event.raw_bit_baselines
    before = event.export()
    event.observe_raw_bit(key, raw_value(source, False))
    assert event.export() == before
    event.feed(b"fresh")
    event.observe_raw_bit(key, raw_value(source, True))
    assert event.events[-1]["active"] is True
    assert event.capture.reason == "recording"
    event.clear()


async def test_three_candidate_edges_share_and_extend_the_same_photo_window():
    event = EventCapture(True)
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 0
        event.feed(b"prehistory")
        for source in SOURCES:
            event.observe_raw_bit(source[0], raw_value(source, False))
        timers = []
        for second, source in enumerate(SOURCES, 10):
            clock.return_value = second
            event.feed(bytes([second]))
            event.observe_raw_bit(source[0], raw_value(source, True))
            timers.append(event.capture.timer)
        assert not event.previous_captures
        assert event.first_event_time == 10
        assert event.capture.monotonic_start == 0
        assert event.capture.recording_duration == 612
        assert [marker["elapsed_ms"] for marker in event.events] == [
            10000,
            11000,
            12000,
        ]
        assert [marker["key"] for marker in event.events] == [s[0] for s in SOURCES]
        assert all(timer.cancelled() for timer in timers[:-1])
        assert not timers[-1].cancelled()
        assert timers[-1].when() == 612
        assert event.summary()["capture_count"] == 1
    event.clear()


async def test_candidate_near_rpm_deadline_extends_but_other_events_do_not():
    event = EventCapture(True)
    source = SOURCES[0]
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 150
        event.feed(b"prehistory")
        event.observe_rpm(0)
        clock.return_value = 170
        event.feed(b"rpm edge")
        event.observe_rpm(1500)
        rpm_timer = event.capture.timer
        assert rpm_timer.when() == 350
        clock.return_value = 348
        event.feed(b"fresh baseline")
        event.observe_rpm(1500)
        event.observe_status("1a100080")
        event.observe_raw_bit(source[0], raw_value(source, False))
        clock.return_value = 349
        event.feed(b"candidate edge")
        event.observe_raw_bit(source[0], raw_value(source, True))
        candidate_timer = event.capture.timer
        assert rpm_timer.cancelled()
        assert candidate_timer.when() == 949
        assert event.capture.recording_duration == 799
        clock.return_value = 350
        event.feed(b"other references")
        event.observe_rpm(0)
        event.observe_status("1a100090")
        result = event.trigger_diagnostic("Photo reference")
        assert result["joined_existing_capture"]
        assert event.capture.timer is candidate_timer
        assert event.capture.recording_duration == 799
        assert [marker["type"] for marker in event.events] == [
            "compressor_started",
            "raw_bit_changed",
            "compressor_stopped",
            "status_0208_bit_28_changed",
            "diagnostic_trigger",
        ]
    event.clear()


async def test_900_second_cap_excludes_prebuffer_and_rotates_instead_of_shortening():
    event = EventCapture(True)
    source = SOURCES[0]
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 0
        event.feed(b"full prehistory")
        clock.return_value = 179
        event.observe_raw_bit(source[0], raw_value(source, False))
        clock.return_value = 180
        event.feed(b"first edge")
        event.observe_raw_bit(source[0], raw_value(source, True))
        first_timer = event.capture.timer
        assert event.pre_seconds == 180
        assert first_timer.when() == 780
        clock.return_value = 400
        event.feed(b"recent prehistory")
        clock.return_value = 480
        event.observe_raw_bit(source[0], raw_value(source, True))
        event.feed(b"edge at exact maximum")
        event.observe_raw_bit(source[0], raw_value(source, False))
        maximum_timer = event.capture.timer
        assert first_timer.cancelled()
        assert maximum_timer.when() == 1080
        assert event.capture.recording_duration == 1080
        assert not event.previous_captures
        clock.return_value = 480.001
        event.feed(b"edge beyond maximum")
        event.observe_raw_bit(source[0], raw_value(source, True))
        assert maximum_timer.cancelled()
        assert len(event.previous_captures) == 1
        previous = event.previous_captures[0]
        assert previous["completion_reason"] == "candidate_retriggered"
        assert previous["actual_duration_seconds"] == pytest.approx(480.001)
        assert previous["duration_seconds"] == 1080
        assert len(previous["events"]) == 2
        assert event.first_event_time == 480.001
        assert event.capture.monotonic_start == 400
        assert event.pre_seconds == pytest.approx(80.001)
        assert event.capture.timer.when() == pytest.approx(1080.001)
        assert event.capture.recording_duration == pytest.approx(680.001)
        assert event.capture.chunks[0]["hex"] == b"recent prehistory".hex()
        assert event.events[0]["elapsed_ms"] == 80001
        assert event.summary()["requested_post_seconds"] == 600
    event.clear()


async def test_retriggered_windows_keep_only_four_and_preserve_fresh_prehistory():
    event = EventCapture(True)
    source = SOURCES[0]
    active = False
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 0
        event.observe_raw_bit(source[0], raw_value(source, active))
        clock.return_value = 1
        event.feed(b"initial edge")
        active = not active
        event.observe_raw_bit(source[0], raw_value(source, active))
        for index in range(1, 6):
            clock.return_value = event.first_event_time + 200
            event.feed(b"recent")
            clock.return_value = event.first_event_time + 300.001
            event.observe_raw_bit(source[0], raw_value(source, active))
            active = not active
            event.feed(bytes([index]))
            event.observe_raw_bit(source[0], raw_value(source, active))
            assert event.pre_seconds == pytest.approx(100.001)
            assert event.capture.chunks[0]["hex"] == b"recent".hex()
            assert event.summary()["capture_count"] == min(index + 1, 4)
        exported = event.export()
        assert len(exported["previous_captures"]) == 3
        assert exported["overwritten_captures"] == 2
        assert all(
            previous["completion_reason"] == "candidate_retriggered"
            for previous in exported["previous_captures"]
        )
        assert all("previous_captures" not in c for c in exported["previous_captures"])
        exported["previous_captures"][0]["events"].clear()
        assert event.export()["previous_captures"][0]["events"]
    event.clear()


async def test_edge_at_due_deadline_preserves_completed_window_and_rearms():
    event = EventCapture(True)
    source = SOURCES[0]
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 0
        event.feed(b"before")
        event.observe_raw_bit(source[0], raw_value(source, False))
        clock.return_value = 10
        event.feed(b"first edge")
        event.observe_raw_bit(source[0], raw_value(source, True))
        old_timer = event.capture.timer
        clock.return_value = 609
        event.feed(b"latest history")
        event.observe_raw_bit(source[0], raw_value(source, True))
        clock.return_value = 610
        event.feed(b"deadline edge")
        event.observe_raw_bit(source[0], raw_value(source, False))
        assert old_timer.cancelled()
        assert event.previous_captures[0]["completion_reason"] == "duration_limit"
        assert event.previous_captures[0]["actual_duration_seconds"] == 610
        assert event.capture.timer.when() == 1210
        assert len(event.events) == 1
        assert event.events[0]["elapsed_ms"] == 1000
        assert event.capture.chunks[-1]["hex"] == b"deadline edge".hex()
        assert event.capture.reason == "recording"
    event.clear()


async def test_extended_timer_stops_without_any_further_receive_data():
    event = EventCapture(True)
    source = SOURCES[0]
    with patch("custom_components.proxon_hesp.event_capture.RAW_BIT_POST_SECONDS", 0.1):
        event.feed(b"before")
        event.observe_raw_bit(source[0], raw_value(source, False))
        event.observe_raw_bit(source[0], raw_value(source, True))
        first_timer = event.capture.timer
        await asyncio.sleep(0.05)
        event.observe_raw_bit(source[0], raw_value(source, False))
        assert first_timer.cancelled()
        await asyncio.sleep(0.07)
        assert event.capture.reason == "recording"
        await asyncio.sleep(0.06)
        assert event.capture.reason == "duration_limit"
        assert event.capture.timer is None
        assert event.status == "ready"
    event.clear()


@pytest.mark.parametrize(
    "limit,reason", [("MAX_BYTES", "byte_limit"), ("MAX_CHUNKS", "chunk_limit")]
)
async def test_candidate_post_window_still_honors_resource_limits(limit, reason):
    event = EventCapture(True)
    source = SOURCES[0]
    event.feed(b"before")
    event.observe_raw_bit(source[0], raw_value(source, False))
    event.observe_raw_bit(source[0], raw_value(source, True))
    timer = event.capture.timer
    maximum = (
        event.capture.size + 1
        if limit == "MAX_BYTES"
        else len(event.capture.chunks) + 1
    )
    with patch("custom_components.proxon_hesp.capture." + limit, maximum):
        event.feed(b"after")
    assert timer.cancelled()
    assert event.capture.reason == reason
    assert event.capture.timer is None
    assert event.summary()["requested_post_seconds"] == 600
    if limit == "MAX_BYTES":
        assert event.capture.size == maximum
        assert event.capture.chunks[-1]["hex"] == b"a".hex()
    else:
        assert len(event.capture.chunks) == maximum
    event.clear()


async def test_omitted_edges_remain_bounded_and_extend_the_photo_window():
    event = EventCapture(True)
    source = SOURCES[0]
    with (
        patch("custom_components.proxon_hesp.event_capture.MAX_EVENTS", 2),
        patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock,
    ):
        clock.return_value = 0
        event.feed(b"before")
        event.observe_raw_bit(source[0], raw_value(source, False))
        for second in range(1, 5):
            clock.return_value = second
            event.feed(bytes([second]))
            event.observe_raw_bit(source[0], raw_value(source, second % 2))
        assert len(event.events) == 2
        assert event.omitted_events == 2
        assert event.capture.timer.when() == 604
        assert not event.previous_captures
    event.clear()


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source[0])
async def test_ha_receive_validates_exact_sources_fragmentation_reconnect_and_no_tx(
    hass, frames, source
):
    streams = []
    reconnected = asyncio.Event()

    async def connect(*args):
        reader = asyncio.StreamReader()
        # Reconnection deliberately starts at the last observed active value.
        reader.feed_data(frames["0xe1"] + source_frame(source, bool(streams)))
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        streams.append((reader, writer))
        if len(streams) == 2:
            reconnected.set()
        return reader, writer

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="raw-bit-passive-unit",
        version=2,
        data={"host": "gateway.test", "port": 4196, "profile": PROFILE},
        options={CONF_EVENT_CAPTURE: True},
    )
    entry.add_to_hass(hass)
    with patch("asyncio.open_connection", side_effect=connect) as connector:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        assert not runtime.event_capture.events
        assert source[0] in runtime.event_capture.raw_bit_baselines
        reader = streams[0][0]
        valid = source_frame(source, True)
        invalid = []
        for offset, value in (
            (0, 0x10),
            (1, 0x81),
            (2, 0 if valid[2] else 7),
            (5, 1),
            (7, 0),
        ):
            body = bytearray(valid[:-2])
            body[offset] = value
            invalid.append(checked(body))
        invalid.append(valid[:-1] + bytes([valid[-1] ^ 1]))
        for frame in invalid:
            reader.feed_data(frame)
            await hass.async_block_till_done()
            assert not runtime.event_capture.events
        reader.feed_data(source_frame(source, False, 0x10))
        await hass.async_block_till_done()
        assert not runtime.event_capture.events

        # Exercise every TCP split through receive() and the real coordinator.
        for split in range(len(valid) + 1):
            runtime.event_capture.clear()
            reader.feed_data(source_frame(source, False))
            await hass.async_block_till_done()
            assert not runtime.event_capture.events
            reader.feed_data(valid[:split])
            await hass.async_block_till_done()
            if split < len(valid):
                assert not runtime.event_capture.events
            reader.feed_data(valid[split:])
            await hass.async_block_till_done()
            assert len(runtime.event_capture.events) == 1
            marker = runtime.event_capture.events[0]
            assert marker["type"] == "raw_bit_changed"
            assert marker["key"] == source[0]
            assert marker["bit"] == source[4]
            assert marker["active"] is True
            assert marker["raw"] == raw_value(source, True)
            assert runtime.event_capture.summary()["requested_post_seconds"] == 600
            assert runtime.application_bytes_sent == 0
        previous_events = list(runtime.event_capture.events)
        reader.feed_eof()
        await asyncio.wait_for(reconnected.wait(), 5)
        await hass.async_block_till_done()
        assert runtime.connected
        assert runtime.reconnects == 1
        assert runtime.event_capture.events == previous_events
        assert runtime.event_capture.capture.reason == "disconnected"
        assert runtime.event_capture.raw_bit_baselines[source[0]][0] is True
        assert connector.call_count == 2
        assert runtime.application_bytes_sent == 0
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert runtime.task is None and runtime.timer is None
        assert runtime.event_capture.capture.timer is None
    for _, writer in streams:
        writer.write.assert_not_called()
        writer.writelines.assert_not_called()
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()
