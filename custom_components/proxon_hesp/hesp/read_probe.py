"""Bounded diagnostic exchange, independent of the passive production receiver.

No socket creation. A future transport owner must provide a coordinated sender.
Only an independently recorded, checksum-verified QUERY can be replayed.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .checksum import checksum


@dataclass(frozen=True)
class ProbeResult:
    dp: int
    response: bytes


class ReadProbe:
    """One exchange at a time; no retries, SETs, or unbounded receive buffer."""

    def __init__(self) -> None:
        self.pending: asyncio.Future | None = None
        self.expected: tuple[int, int] | None = None
        self.buffer = bytearray()
        self.bytes_submitted = 0
        self.last_status = "idle"

    async def run(
        self,
        query: bytes,
        response_size: int,
        send: Callable[[bytes], Awaitable[None]],
        *,
        coordinated: bool = False,
    ) -> ProbeResult:
        """Sender owns arbitration; false is the default and rejects transmission."""
        if not coordinated:
            raise ValueError("Bus coordination is not established")
        if self.pending is not None:
            raise RuntimeError("A probe is already pending")
        if (
            len(query) != 12
            or query[:3] != b"\x10\x80\x00"
            or query[5:8] != b"\x00\x00\x04"
            or checksum(query[:-2]) != int.from_bytes(query[-2:], "little")
            or response_size not in (1, 2, 4)
        ):
            raise ValueError("Unsupported query or response shape")
        dp = int.from_bytes(query[3:5], "little")
        # First diagnostic target only: previously observed filter-days query.
        if dp != 0x00ED or query[8:10] != b"\x01\x00" or response_size != 4:
            raise ValueError("Only the observed filter-days read is allowed")
        self.pending = asyncio.get_running_loop().create_future()
        self.expected = dp, response_size
        self.buffer.clear()
        self.last_status = "pending"
        try:
            async with asyncio.timeout(3):
                self.bytes_submitted += len(query)
                await send(query)
                result = await self.pending
            self.last_status = "response_observed"
            return result
        except TimeoutError:
            self.last_status = "timeout"
            raise
        except asyncio.CancelledError:
            self.last_status = "cancelled"
            raise
        except Exception:
            self.last_status = "failed"
            raise
        finally:
            if self.pending is not None and not self.pending.done():
                self.pending.cancel()
            self.pending = None
            self.expected = None
            self.buffer.clear()

    def feed(self, data: bytes) -> None:
        """Match exact identity and checksum; retain only an incomplete frame."""
        if self.pending is None or self.pending.done() or self.expected is None:
            return
        dp, size = self.expected
        header = b"\x22\x40\x00" + dp.to_bytes(2, "little")
        header += b"\x00\x00" + bytes([size * 2])
        length = 10 + size
        # Byte-wise processing keeps memory bounded even for a huge input chunk.
        for byte in data:
            self.buffer.append(byte)
            if len(self.buffer) < length:
                continue
            frame = bytes(self.buffer)
            if frame[:8] == header and checksum(frame[:-2]) == int.from_bytes(
                frame[-2:], "little"
            ):
                self.pending.set_result(ProbeResult(dp, frame))
                self.buffer.clear()
                return
            del self.buffer[0]
