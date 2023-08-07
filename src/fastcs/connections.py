import asyncio
from dataclasses import dataclass


class DisconnectedError(Exception):
    pass


@dataclass
class IPConnectionSettings:
    ip: str = "127.0.0.1"
    port: int = 25565


class IPConnection:
    def __init__(self):
        self._reader, self._writer = (None, None)
        self._lock = asyncio.Lock()

    async def connect(self, settings: IPConnectionSettings):
        self._reader, self._writer = await asyncio.open_connection(
            settings.ip, settings.port
        )

    def ensure_connected(self):
        if self._reader is None or self._writer is None:
            raise DisconnectedError("Need to call connect() before using IPConnection.")

    async def send_command(self, message) -> None:
        async with self._lock:
            self.ensure_connected()
            await self._send_message(message)

    async def send_query(self, message) -> str:
        async with self._lock:
            self.ensure_connected()
            await self._send_message(message)
            return await self._receive_response()

    # TODO: Figure out type hinting for connections. TypeGuard fails to work as expected
    async def close(self):
        async with self._lock:
            self.ensure_connected()
            self._writer.close()
            await self._writer.wait_closed()
            self._reader, self._writer = (None, None)

    async def _send_message(self, message) -> None:
        self._writer.write(message.encode("utf-8"))
        await self._writer.drain()

    async def _receive_response(self) -> str:
        data = await self._reader.readline()
        return data.decode("utf-8")
