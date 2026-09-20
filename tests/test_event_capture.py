"""Bounded event recording and transition detection, without a second parser."""

import asyncio
from unittest.mock import patch

import pytest

from custom_components.proxon_hesp.event_capture import EventCapture


async def test_pre_post_order_retention_and_rearm():
    e = EventCapture(True)
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        e.feed(b"before")
        e.observe_rpm(0)
        clock.return_value = 110
        e.feed(b"trigger")
        e.observe_rpm(2000)
        timer = e.capture.timer
        assert e.pre_seconds == 10
        assert e.events[0]["elapsed_ms"] == 10000
        assert e.events[0]["type"] == "compressor_started"
        assert e.capture.recording_duration == 190
        clock.return_value = 120
        e.feed(b"after")
        e.observe_rpm(0)
        assert e.events[1]["type"] == "compressor_stopped"
        assert e.capture.timer is timer
        assert (
            b"".join(bytes.fromhex(c["hex"]) for c in e.export()["chunks"])
            == b"beforetriggerafter"
        )
        clock.return_value = 290
        e.feed(b"too late")
        assert e.status == "ready"
        assert e.capture.reason == "duration_limit"
        saved = e.export()
        e.feed(b"next")
        e.observe_rpm(2000)
        assert e.export() == saved
        e.clear()
        assert e.status == "waiting"
        e.feed(b"baseline")
        e.observe_rpm(2000)
        assert not e.events
        e.observe_rpm(0)
        assert e.events[0]["type"] == "compressor_stopped"
    e.clear()
    assert e.capture.timer is None


async def test_opt_in_stale_baseline_disconnect_and_disable():
    e = EventCapture()
    e.feed(b"ignored")
    e.observe_rpm(100)
    assert not e.ring and e.baseline is None
    e.configure(True)
    with patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock:
        clock.return_value = 100
        e.observe_rpm(0)
        clock.return_value = 130
        e.observe_rpm(100)
        assert e.status == "waiting"  # expired zero must not trigger
        e.disconnect()
        e.observe_rpm(0)
        assert e.status == "waiting"
        e.observe_rpm(100)
        assert e.status == "recording"
        e.configure(False)
        assert e.status == "ready"
        assert e.capture.reason == "disabled"
        assert e.capture.timer is None
        saved = e.export()
        e.configure(True)
        e.observe_rpm(0)
        assert e.events == saved["events"]
        e.clear()
        e.observe_rpm(0)
        e.observe_rpm(100)
        e.disconnect()
        assert e.capture.reason == "disconnected"
        assert e.capture.timer is None
    e.clear()


async def test_ring_time_byte_chunk_and_event_bounds():
    e = EventCapture(True)
    with (
        patch("custom_components.proxon_hesp.event_capture.time.monotonic") as clock,
        patch("custom_components.proxon_hesp.event_capture.RING_BYTES", 10),
        patch("custom_components.proxon_hesp.event_capture.RING_CHUNKS", 2),
        patch("custom_components.proxon_hesp.event_capture.MAX_EVENTS", 2),
    ):
        clock.return_value = 0
        e.feed(b"old")
        clock.return_value = 61
        e.feed(b"new")
        assert list(e.ring) == [(61, b"new")]
        e.feed(b"x" * 100)
        assert e.ring_size == 10
        e.feed(b"a")
        e.feed(b"b")
        e.feed(b"c")
        assert len(e.ring) == 2
        assert e.ring_size == 2
        e.observe_rpm(0)
        for rpm in (100, 0, 100, 0):
            e.observe_rpm(rpm)
        assert len(e.events) == 2 and e.omitted_events == 2
    e.clear()


async def test_timer_finishes_without_new_traffic():
    e = EventCapture(True)
    e.capture.duration = 0.01
    e.observe_rpm(0)
    e.observe_rpm(100)
    await asyncio.sleep(0.03)
    assert e.status == "ready"
    assert e.capture.reason == "duration_limit"
    assert e.capture.timer is None
    e.clear()


@pytest.mark.parametrize(
    "limit,reason", [("MAX_BYTES", "byte_limit"), ("MAX_CHUNKS", "chunk_limit")]
)
async def test_post_capture_resource_limit(limit, reason):
    e = EventCapture(True)
    e.observe_rpm(0)
    e.observe_rpm(100)
    with patch("custom_components.proxon_hesp.capture." + limit, 1):
        e.feed(b"traffic")
    assert e.status == "ready"
    assert e.capture.reason == reason
    assert e.capture.timer is None
    e.clear()


@pytest.mark.parametrize(
    "tool", ["inventory_capture", "replay_diagnosis", "compare_captures"]
)
def test_existing_cli_selects_event_export(tool, tmp_path):
    import importlib
    import json

    from tests.test_operating_telemetry import HEATING

    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "data": {
                    "capture": {"chunks": []},
                    "event_capture": {
                        "format_version": 2,
                        "chunks": [{"elapsed_ms": 0, "hex": HEATING.hex()}],
                    },
                }
            }
        )
    )
    output = tmp_path / "result.json"
    argv = [tool, str(source), "--event", "--output", str(output)]
    if tool == "compare_captures":
        argv += ["--report", str(tmp_path / "report.md")]
    with patch("sys.argv", argv):
        importlib.import_module("tools." + tool).main()
    assert output.exists()
    text = output.read_text()
    assert (
        ("compressor_rpm" in text) if tool == "replay_diagnosis" else ("051C" in text)
    )


def test_event_translations():
    import json
    from pathlib import Path

    from custom_components.proxon_hesp.event_capture import EVENT_STATUSES

    for file in ("strings.json", "translations/en.json", "translations/de.json"):
        d = json.loads((Path("custom_components/proxon_hesp") / file).read_text())
        assert set(d["entity"]["sensor"]["event_capture_status"]["state"]) == set(
            EVENT_STATUSES
        )
        assert d["entity"]["button"]["event_capture_clear"]["name"]
        assert d["options"]["step"]["init"]["data"]["event_capture_enabled"]
