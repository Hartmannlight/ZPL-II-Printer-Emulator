import asyncio

from zpl_printer_emulator.tcp_server import TcpPrinterServer


async def test_tcp_server_collects_payload() -> None:
    received: list[bytes] = []

    async def handler(payload: bytes) -> None:
        received.append(payload)

    server = TcpPrinterServer("127.0.0.1", 0, handler)
    await server.start()
    assert server._server is not None
    socket = server._server.sockets[0]
    host, port = socket.getsockname()[:2]

    reader, writer = await asyncio.open_connection(host, port)
    writer.write(b"^XA^FO10,10^FDHello^FS^XZ")
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    for _ in range(20):
        if received:
            break
        await asyncio.sleep(0.01)

    await server.stop()
    assert received == [b"^XA^FO10,10^FDHello^FS^XZ"]
