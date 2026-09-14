"""Recorded replies exercise bounded matching without a gateway connection."""

import asyncio

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.read_probe import ReadProbe
from tests.test_controller import FRAMES


def query():
    message = bytes.fromhex("108000ed000000040100")
    return message + checksum(message).to_bytes(2, "little")


async def test_default_blocks_before_sender():
    async def send(_):
        pytest.fail("No sending without coordination")

    with pytest.raises(ValueError):
        await ReadProbe().run(query(), 4, send)


async def test_split_response_and_corruption():
    probe = ReadProbe()
    response = FRAMES["0x00ed"]

    async def send(frame):
        assert frame == query()
        probe.feed(b"x" * 10000)
        assert len(probe.buffer) < 14
        probe.feed(response[:-1] + bytes([response[-1] ^ 1]))
        probe.feed(FRAMES["0x02d0"])
        for byte in response:
            probe.feed(bytes([byte]))

    result = await probe.run(query(), 4, send, coordinated=True)
    assert result.response == response
    assert probe.bytes_submitted == 12
    assert probe.last_status == "response_observed"
    assert probe.pending is None


async def test_cancel_cleans_pending():
    probe = ReadProbe()
    started = asyncio.Event()

    async def send(_):
        started.set()

    task = asyncio.create_task(probe.run(query(), 4, send, coordinated=True))
    await started.wait()
    with pytest.raises(RuntimeError):
        await probe.run(query(), 4, send, coordinated=True)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert probe.pending is None
    assert not probe.buffer
    assert probe.last_status == "cancelled"


async def test_timeout_does_not_retry():
    probe = ReadProbe()
    calls = []

    async def send(frame):
        calls.append(frame)

    with pytest.raises(TimeoutError):
        await probe.run(query(), 4, send, coordinated=True)
    assert calls == [query()]
    assert probe.last_status == "timeout"
    assert probe.pending is None


async def test_set_is_never_sent():
    async def send(_):
        pytest.fail("SET must not reach transport")

    with pytest.raises(ValueError):
        await ReadProbe().run(FRAMES["0x00ed"], 4, send, coordinated=True)
