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
        assert capture.reason == "size_limit"
        assert capture.timer is None
    with patch("custom_components.proxon_hesp.capture.MAX_CHUNKS", 2):
        capture.start()
        capture.feed(b"a")
        capture.feed(b"b")
        capture.feed(b"c")
        assert len(capture.chunks) == 2
        assert capture.reason == "size_limit"


async def test_timeout_even_without_traffic():
    capture = Capture()
    with patch("custom_components.proxon_hesp.capture.DURATION", 0.001):
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
