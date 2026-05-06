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
        chunks: list[bytes] = []
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            payload = b"".join(chunks)
            if payload:
                await self._handler(payload)
        finally:
            writer.close()
            await writer.wait_closed()
