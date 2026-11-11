"""Original receive timestamps, bounded snapshots and unchanged capture ownership."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from custom_components.proxon_hesp import event_capture
from custom_components.proxon_hesp.diagnostics import async_get_config_entry_diagnostics
from custom_components.proxon_hesp.event_capture import EventCapture
from tests.test_capture_diagnostics import diagnostic_setup as diagnostic_setup
from tests.test_fan_diagnostics import LEVEL_TWO_80001312_FRAME

BASE = datetime(2000, 1, 1, tzinfo=UTC)


@pytest.fixture
def receive_clock(monkeypatch):
    clock = SimpleNamespace(monotonic=0.0, wall=BASE)

    class ReceiveDateTime(datetime):
        @classmethod
        def now(cls, tz):
            assert tz is UTC
            return cls.fromtimestamp(clock.wall.timestamp(), UTC)

    monkeypatch.setattr(event_capture, "datetime", ReceiveDateTime)
    monkeypatch.setattr(event_capture.time, "monotonic", lambda: clock.monotonic)

    def advance(seconds, wall_offset=0):
        clock.monotonic = seconds
        clock.wall = BASE + timedelta(seconds=seconds + wall_offset)

    clock.advance = advance
    return clock


def test_empty_disabled_and_expired_exports_do_not_change_the_ring(receive_clock):
    capture = EventCapture()
    capture.feed(b"disabled")
    assert capture.export_recent_received() is None
    assert not capture.ring
    capture.configure(True)
    assert capture.export_recent_received() is None
    capture.feed(b"old")
    before = list(capture.ring)
    receive_clock.advance(180)
    assert capture.export_recent_received()["chunks"][0]["hex"] == b"old".hex()
    receive_clock.advance(180.001)
    assert capture.export_recent_received() is None
    assert list(capture.ring) == before


def test_snapshot_preserves_actual_receive_utc_without_starting_or_clearing(
    receive_clock,
):
    changed = Mock()
    capture = EventCapture(True, changed)
    capture.feed(b"first")
    receive_clock.advance(5.392342)
    capture.feed(b"second")
    before = deepcopy(capture.export()), list(capture.ring), capture.ring_size
    receive_clock.advance(9.5)
    with (
        patch.object(capture.capture, "start") as start,
        patch.object(capture.capture, "stop") as stop,
        patch.object(capture.capture, "clear") as clear,
    ):
        snapshot = capture.export_recent_received()
        start.assert_not_called()
        stop.assert_not_called()
        clear.assert_not_called()
    assert snapshot == {
        "format_version": 1,
        "source_kind": "passive_received_snapshot",
        "status": "partial",
        "completion_reason": "passive_snapshot",
        "timestamp_basis": "original_received_utc_and_monotonic_elapsed",
        "started_utc": BASE.isoformat(),
        "received_until_utc": (BASE + timedelta(seconds=5.392342)).isoformat(),
        "exported_at_utc": (BASE + timedelta(seconds=9.5)).isoformat(),
        "chunks": [
            {"elapsed_ms": 0, "received_utc": BASE.isoformat(), "hex": b"first".hex()},
            {
                "elapsed_ms": 5392,
                "received_utc": (BASE + timedelta(seconds=5.392342)).isoformat(),
                "hex": b"second".hex(),
            },
        ],
        "bytes": 11,
        "chunk_count": 2,
        "max_age_seconds": 180,
        "max_bytes": 524288,
        "max_chunks": 8192,
        "prefix_bytes_omitted": 0,
        "clock_skew_tolerance_seconds": 1.0,
    }
    snapshot["chunks"][0]["hex"] = "00"
    assert capture.export_recent_received()["chunks"][0]["hex"] == b"first".hex()
    assert (capture.export(), list(capture.ring), capture.ring_size) == before
    assert capture.capture.reason == "idle" and not capture.events
    assert capture.capture.timer is None
    changed.assert_not_called()


def test_byte_and_chunk_limits_keep_original_utc_and_report_truncated_prefix(
    receive_clock, monkeypatch
):
    monkeypatch.setattr(event_capture, "RING_BYTES", 10)
    monkeypatch.setattr(event_capture, "RING_CHUNKS", 2)
    capture = EventCapture(True)
    capture.feed(b"0123456789abcdef")
    snapshot = capture.export_recent_received()
    assert snapshot["chunks"][0]["hex"] == b"6789abcdef".hex()
    assert snapshot["chunks"][0]["received_utc"] == BASE.isoformat()
    assert snapshot["prefix_bytes_omitted"] == 6
    assert snapshot["bytes"] == snapshot["max_bytes"] == 10
    for second, payload in enumerate((b"a", b"b", b"c"), 1):
        receive_clock.advance(second)
        capture.feed(payload)
    snapshot = capture.export_recent_received()
    assert [row["hex"] for row in snapshot["chunks"]] == [b"b".hex(), b"c".hex()]
    assert snapshot["started_utc"] == (BASE + timedelta(seconds=2)).isoformat()
    assert snapshot["chunk_count"] == snapshot["max_chunks"] == 2
    assert snapshot["bytes"] == 2 and snapshot["prefix_bytes_omitted"] == 0


@pytest.mark.parametrize("jump", (-2, 2))
@pytest.mark.parametrize("phase", ("receive", "export"))
def test_clock_jumps_fail_closed_without_changing_received_data(
    receive_clock, jump, phase
):
    capture = EventCapture(True)
    capture.feed(b"before")
    receive_clock.advance(10, jump)
    if phase == "receive":
        capture.feed(b"after")
    before = list(capture.ring)
    assert capture.export_recent_received() is None
    assert list(capture.ring) == before


def test_even_small_backwards_receive_times_are_not_reordered(receive_clock):
    capture = EventCapture(True)
    capture.feed(b"first")
    receive_clock.advance(0.5)
    capture.feed(b"second")
    receive_clock.advance(0.6, -0.2)
    capture.feed(b"backwards")
    assert capture.export_recent_received() is None


def test_legacy_ring_without_pinned_utc_is_not_backdated_at_export(receive_clock):
    capture = EventCapture(True)
    capture.ring.append((0.0, b"legacy"))
    capture.ring_size = 6
    receive_clock.advance(1)
    assert capture.export_recent_received() is None
    assert list(capture.ring) == [(0.0, b"legacy")]


def test_disconnect_clear_and_opt_out_never_join_connection_epochs(receive_clock):
    capture = EventCapture(True)
    capture.feed(b"old connection")
    capture.disconnect()
    assert capture.export_recent_received() is None
    receive_clock.advance(20)
    capture.feed(b"new connection")
    snapshot = capture.export_recent_received()
    assert snapshot["started_utc"] == (BASE + timedelta(seconds=20)).isoformat()
    assert len(snapshot["chunks"]) == 1
    assert snapshot["chunks"][0]["hex"] == b"new connection".hex()
    capture.clear()
    assert capture.export_recent_received() is None
    capture.feed(b"before opt-out")
    capture.configure(False)
    capture.feed(b"ignored")
    assert capture.export_recent_received() is None
    capture.configure(True)
    assert capture.export_recent_received() is None


async def test_passive_read_does_not_change_an_active_event_window(receive_clock):
    capture = EventCapture(True)
    capture.feed(b"before")
    capture.observe_rpm(0)
    receive_clock.advance(10)
    capture.feed(b"edge")
    capture.observe_rpm(2000)
    timer = capture.capture.timer
    before = capture.export()
    snapshot = capture.export_recent_received()
    assert snapshot["chunks"][-1]["elapsed_ms"] == 10000
    assert capture.export() == before
    assert capture.capture.timer is timer
    assert capture.status == "recording" and len(capture.events) == 1
    assert before["chunks"] == [
        {"elapsed_ms": 0, "hex": b"before".hex()},
        {"elapsed_ms": 10000, "hex": b"edge".hex()},
    ]
    capture.clear()


async def test_existing_diagnostic_envelope_exposes_passive_bytes_without_sends(
    hass, diagnostic_setup
):
    entry, streams, _ = diagnostic_setup
    runtime = entry.runtime_data
    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostic["event_capture"]["passive_capture"] is None
    runtime.event_capture.configure(True)
    frame = bytes.fromhex(LEVEL_TWO_80001312_FRAME)
    streams[-1][0].feed_data(frame)
    await hass.async_block_till_done()
    before = runtime.event_capture.export()
    task = runtime.task
    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    received = diagnostic["event_capture"].pop("passive_capture")
    assert received["source_kind"] == "passive_received_snapshot"
    assert received["chunks"][0]["hex"] == frame.hex()
    assert received["started_utc"] == received["received_until_utc"]
    assert diagnostic["event_capture"] == {
        **before,
        "integration_version": runtime.integration_version,
        "profile": runtime.profile,
    }
    assert runtime.event_capture.export() == before and runtime.task is task
    assert runtime.application_bytes_sent == 0
    assert runtime.capture.reason == runtime.event_capture.capture.reason == "idle"
    for _, writer in streams:
        writer.write.assert_not_called()
        writer.writelines.assert_not_called()
