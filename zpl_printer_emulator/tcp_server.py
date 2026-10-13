from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


ZplHandler = Callable[[bytes], Awaitable[None]]


class TcpPrinterServer:
    def __init__(self, host: str, port: int, handler: ZplHandler) -> None:
        self._host = host
        self._port = port
        self._handler = handler
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self._host, self._port)

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        buffer = b''
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                buffer += chunk
                while True:
                    start = buffer.find(b'^XA')
                    if start < 0:
                        # Retain a possible marker split across TCP packets.
                        buffer = buffer[-2:]
                        break
                    buffer = buffer[start:]
                    end = buffer.find(b'^XZ', 3)
                    if end < 0:
                        break
                    label, buffer = buffer[:end + 3], buffer[end + 3:]
                    await self._handler(label)
        finally:
            writer.close()
            await writer.wait_closed()
