"""No application sends, correct cancellation and bounded observation window."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.proxon_hesp.hesp.decoder import Decoder
from custom_components.proxon_hesp.hesp.transport import NoSupportedData, probe, receive


async def test_probe_never_sends_and_closes(frames):
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])
    writer = MagicMock()
    writer.wait_closed = AsyncMock()
    with patch("asyncio.open_connection", return_value=(reader, writer)):
        await probe("gateway.test", 4196)
    writer.write.assert_not_called()
    writer.writelines.assert_not_called()
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()


async def test_no_data_timeout_closes():
    reader = asyncio.StreamReader()
    writer = MagicMock()
    writer.wait_closed = AsyncMock()
    with patch("asyncio.open_connection", return_value=(reader, writer)):
        with pytest.raises(NoSupportedData):
            await probe("gateway.test", 4196, timeout=0.01)
    writer.close.assert_called_once()
    writer.write.assert_not_called()


async def test_eof_is_not_success():
    reader = asyncio.StreamReader()
    reader.feed_eof()
    with pytest.raises(ConnectionError):
        async for _ in receive(reader, Decoder()):
            pytest.fail("EOF must not yield data")


async def test_cancellation_closes():
    reader = asyncio.StreamReader()
    writer = MagicMock()
    writer.wait_closed = AsyncMock()
    opened = asyncio.Event()

    async def connect(*args):
        opened.set()
        return reader, writer

    with patch("asyncio.open_connection", side_effect=connect):
        task = asyncio.create_task(probe("gateway.test", 4196))
        await opened.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    writer.close.assert_called_once()
