"""Receive-only TCP session. No writes, polling requests or gateway changes."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress

from .decoder import Decoder, Reading


class NoSupportedData(Exception):
    """TCP works but the supported checksum-verified HESP subset was not seen."""


@asynccontextmanager
async def open_receiver(host: str, port: int):
    """Close the stream on cancellation, setup failure, EOF and normal exit."""
    async with asyncio.timeout(5):
        reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader
    finally:
        writer.close()
        with suppress(OSError, TimeoutError):
            async with asyncio.timeout(2):
                await writer.wait_closed()


async def receive(
    reader: asyncio.StreamReader,
    decoder: Decoder,
    timeout: float = 30,
    on_data: Callable[[bytes], None] | None = None,
) -> AsyncIterator[list[Reading]]:
    """Require supported data periodically, not merely an open socket."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise NoSupportedData
        try:
            async with asyncio.timeout(remaining):
                data = await reader.read(4096)
        except TimeoutError as err:
            raise NoSupportedData from err
        if not data:
            raise ConnectionError("Gateway closed the connection")
        if on_data is not None:
            on_data(data)
        readings = decoder.feed(data)
        if readings:
            deadline = loop.time() + timeout
            yield readings


async def probe(host: str, port: int, timeout: float = 20) -> None:
    """Validate passive reception without persisting any measurements."""
    async with open_receiver(host, port) as reader:
        async for _readings in receive(reader, Decoder(), timeout):
            return
