"""Capture boundaries, lifecycle and passive stream hook."""

import asyncio
from unittest.mock import patch

from custom_components.proxon_hesp.capture import Capture
from custom_components.proxon_hesp.hesp.decoder import Decoder
from custom_components.proxon_hesp.hesp.transport import receive


async def test_opt_in_snapshot_stop_clear():
    capture = Capture()
    capture.feed(b"ignored")
    assert capture.export()["chunks"] == []
    capture.start()
    capture.feed(b"\x00\xff")
    snapshot = capture.export()
    snapshot["chunks"][0]["hex"] = "changed"
    assert capture.export()["chunks"][0]["hex"] == "00ff"
    capture.stop()
    capture.feed(b"ignored")
    assert capture.size == 2
    capture.clear()
    assert capture.timer is None
    assert capture.export()["chunks"] == []


async def test_size_and_chunk_limits():
    capture = Capture()
    with patch("custom_components.proxon_hesp.capture.MAX_BYTES", 3):
        capture.start()
        capture.feed(b"abcdef")
        assert capture.size == 3
        assert capture.reason == "byte_limit"
        assert capture.timer is None
    with patch("custom_components.proxon_hesp.capture.MAX_CHUNKS", 2):
        capture.start()
        capture.feed(b"a")
        capture.feed(b"b")
        capture.feed(b"c")
        assert len(capture.chunks) == 2
        assert capture.reason == "chunk_limit"


async def test_timeout_even_without_traffic():
    capture = Capture()
    with patch.object(capture, "duration", 0.001):
        capture.start()
        await asyncio.sleep(0.01)
    assert capture.reason == "duration_limit"
    assert capture.timer is None


async def test_hook_captures_unknown_bytes_before_decoder(frames):
    reader = asyncio.StreamReader()
    data = b"unknown" + frames["0xe1"]
    reader.feed_data(data)
    capture = Capture()
    capture.start()
    stream = receive(reader, Decoder(), on_data=capture.feed)
    assert (await anext(stream))[0].value == 3
    assert capture.chunks[0]["hex"] == data.hex()
    await stream.aclose()
    capture.clear()


async def test_duration_stop_restart_and_atomic_notifications():
    from types import SimpleNamespace

    events = []
    clock = SimpleNamespace(monotonic=lambda: 100.0)
    capture = Capture(30, lambda: events.append(capture.summary()))
    with patch("custom_components.proxon_hesp.capture.time", clock):
        capture.start()
        original_timer = capture.timer
        clock.monotonic = lambda: 104.125
        capture.feed(b"a")
        # Chunk arrivals do not publish entity changes at bus frequency.
        assert len(events) == 1
        capture.stop()
        assert events[-1]["actual_duration_seconds"] == 4.125
        assert events[-1]["stopped_utc"] is not None
        clock.monotonic = lambda: 200.0
        assert capture.summary()["actual_duration_seconds"] == 4.125
        capture.stop("disconnected")
        assert capture.reason == "manual"
        assert len(events) == 2
        capture.duration = 600
        capture.start()
        assert original_timer.cancelled()
        assert capture.recording_duration == 600
        assert capture.size == 0
        assert capture.stopped is None
        replaced_timer = capture.timer
        capture.start()
        assert replaced_timer.cancelled()
        assert [event["status"] for event in events] == [
            "recording",
            "manual",
            "recording",
            "recording",
        ]
        capture.clear()
        assert events[-1]["status"] == "idle"
        assert events[-1]["actual_duration_seconds"] == 0
        assert capture.timer is None


async def test_overdue_timer_does_not_admit_more_data():
    from types import SimpleNamespace

    clock = SimpleNamespace(monotonic=lambda: 0.0)
    capture = Capture(30)
    with patch("custom_components.proxon_hesp.capture.time", clock):
        capture.start()
        capture.feed(b"")
        assert not capture.chunks
        clock.monotonic = lambda: 31.0
        capture.feed(b"too late")
        assert capture.reason == "duration_limit"
        assert capture.size == 0
        assert capture.summary()["actual_duration_seconds"] == 31
        assert capture.timer is None


def test_duration_bounds():
    import pytest

    for duration in (0, 29, 601, True, 30.5, "120", None):
        with pytest.raises(ValueError):
            Capture(duration)
    assert Capture().duration == 120
    assert Capture(600).duration == 600
