import asyncio
from dataclasses import dataclass

import aioserial


class NotOpenedError(Exception):
    pass


@dataclass
class SerialConnectionSettings:
    port: str
    baud: int = 115200


class SerialConnection:
    def __init__(self):
        self.stream = None
        self._lock = asyncio.Lock()

    async def connect(self, settings: SerialConnectionSettings) -> None:
        self.stream = aioserial.AioSerial(port=settings.port, baudrate=settings.baud)

    def ensure_open(self):
        if self.stream is None:
            raise NotOpenedError(
                "Need to call connect() before using SerialConnection."
            )

    async def send_command(self, message: bytes) -> None:
        async with self._lock:
            self.ensure_open()
            await self._send_message(message)

    async def send_query(self, message: bytes, response_size: int) -> bytes:
        async with self._lock:
            self.ensure_open()
            await self._send_message(message)
            return await self._receive_response(response_size)

    async def close(self) -> None:
        async with self._lock:
            self.ensure_open()
            self.stream.close()
            self.stream = None

    async def _send_message(self, message):
        await self.stream.write_async(message)

    async def _receive_response(self, size):
        return await self.stream.read_async(size)
