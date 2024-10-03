import asyncio
from dataclasses import dataclass
from types import TracebackType


class DisconnectedError(Exception):
    pass


@dataclass
class IPConnectionSettings:
    ip: str = "127.0.0.1"
    port: int = 25565


@dataclass
class StreamConnection:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    def __post_init__(self):
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        self._lock.release()

    async def send_message(self, message: str) -> None:
        self.writer.write(message.encode("utf-8"))
        await self.writer.drain()

    async def receive_response(self) -> str:
        data = await self.reader.readline()
        return data.decode("utf-8")

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()


class IPConnection:
    def __init__(self):
        self.__connection = None

    @property
    def _connection(self) -> StreamConnection:
        if self.__connection is None:
            raise DisconnectedError("Need to call connect() before using IPConnection.")

        return self.__connection

    async def connect(self, settings: IPConnectionSettings):
        reader, writer = await asyncio.open_connection(settings.ip, settings.port)
        self.__connection = StreamConnection(reader, writer)

    async def send_command(self, message: str) -> None:
        async with self._connection as connection:
            await connection.send_message(message)

    async def send_query(self, message: str) -> str:
        async with self._connection as connection:
            await connection.send_message(message)
            return await connection.receive_response()

    async def close(self):
        async with self._connection as connection:
            await connection.close()
            self.__connection = None
