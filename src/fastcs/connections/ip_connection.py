import asyncio
import codecs
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, cast

_AsyncFuncType = Callable[..., Coroutine[Any, Any, Any]]


def _with_lock(func: _AsyncFuncType) -> _AsyncFuncType:
    async def with_lock(*args: Any, **kwargs: Any) -> None:
        self = args[0]
        async with self.lock:
            await func(*args, **kwargs)

    return cast(_AsyncFuncType, with_lock)


def _ensure_connected(func: _AsyncFuncType) -> _AsyncFuncType:
    """
    Decorator function to check if the wrapper is connected to the device
    before calling the attached function.

    Args:
        func: Function to call if connected to device

    Returns:
        The wrapped function.

    """

    async def check_connected(*args: Any, **kwargs: Any) -> None:
        self = args[0]
        if self._reader is None or self._writer is None:
            raise DisconnectedError("Need to call connect() before using IPConnection.")
        else:
            await func(*args, **kwargs)

    return cast(_AsyncFuncType, check_connected)


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
        self.connected: bool = False

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    async def connect(self, settings: IPConnectionSettings):
        self._reader, self._writer = await asyncio.open_connection(
            settings.ip, settings.port
        )

    @_with_lock
    @_ensure_connected
    async def send_command(self, message: str) -> None:
        await self._send_message(message)

    @_with_lock
    @_ensure_connected
    async def send_query(self, message: str) -> str:
        await self._send_message(message)
        return await self._receive_response()

    # TODO: Figure out type hinting for connections. TypeGuard fails to work as expected
    @_with_lock
    @_ensure_connected
    async def close(self):
        assert isinstance(self._writer, asyncio.StreamWriter)
        self._writer.close()
        await self._writer.wait_closed()
        self._reader, self._writer = (None, None)

    async def _send_message(self, message: str) -> None:
        assert isinstance(self._writer, asyncio.StreamWriter)
        self._writer.write(codecs.encode(message, "utf-8"))
        await self._writer.drain()

    async def _receive_response(self) -> str:
        assert isinstance(self._reader, asyncio.StreamReader)
        data = await self._reader.readline()
        return codecs.decode(data, "utf-8")
