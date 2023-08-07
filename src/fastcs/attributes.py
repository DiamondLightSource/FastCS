from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Protocol

from .datatypes import ATTRIBUTE_TYPES, AttrCallback, DataType, T


class AttrMode(Enum):
    READ = 1
    WRITE = 2
    READ_WRITE = 3


class Sender(Protocol):
    async def put(self, controller: Any, attr: AttrW, value: Any) -> None:
        pass


class Updater(Protocol):
    update_period: float

    async def update(self, controller: Any, attr: AttrR) -> None:
        pass


class Handler(Sender, Updater, Protocol):
    pass


class Attribute(Generic[T]):
    def __init__(
        self, datatype: DataType[T], mode: AttrMode, handler: Any = None
    ) -> None:
        assert (
            datatype.dtype in ATTRIBUTE_TYPES
        ), f"Attr type must be one of {ATTRIBUTE_TYPES}, received type {datatype.dtype}"
        self._datatype: DataType[T] = datatype
        self._mode: AttrMode = mode

    @property
    def datatype(self) -> DataType[T]:
        return self._datatype

    @property
    def dtype(self) -> type[T]:
        return self._datatype.dtype

    @property
    def mode(self) -> AttrMode:
        return self._mode


class AttrR(Attribute[T]):
    def __init__(
        self,
        datatype: DataType[T],
        mode=AttrMode.READ,
        handler: Updater | None = None,
    ) -> None:
        super().__init__(datatype, mode=mode, handler=handler)  # type: ignore
        self._value: T = datatype.dtype()
        self._update_callback: AttrCallback[T] | None = None
        self._updater = handler

    def get(self) -> T:
        return self._value

    async def set(self, value: T) -> None:
        self._value = self._datatype.dtype(value)

        if self._update_callback is not None:
            await self._update_callback(self._value)

    def set_update_callback(self, callback: AttrCallback[T] | None) -> None:
        self._update_callback = callback

    @property
    def updater(self) -> Updater | None:
        return self._updater


class AttrW(Attribute[T]):
    def __init__(
        self, datatype: DataType[T], mode=AttrMode.WRITE, handler: Sender | None = None
    ) -> None:
        super().__init__(datatype, mode=mode, handler=handler)  # type: ignore
        self._process_callback: AttrCallback[T] | None = None
        self._write_display_callback: AttrCallback[T] | None = None
        self._sender = handler

    async def process(self, value: T) -> None:
        if self._write_display_callback is not None:
            await self._write_display_callback(self._datatype.dtype(value))

        await self.process_without_display_update(value)

    async def process_without_display_update(self, value: T) -> None:
        if self._process_callback is not None:
            await self._process_callback(self._datatype.dtype(value))

    def set_process_callback(self, callback: AttrCallback[T] | None) -> None:
        self._process_callback = callback

    def has_process_callback(self) -> bool:
        return self._process_callback is not None

    def set_write_display_callback(self, callback: AttrCallback[T] | None) -> None:
        self._write_display_callback = callback

    @property
    def sender(self) -> Sender | None:
        return self._sender


class AttrRW(AttrW[T], AttrR[T]):
    def __init__(
        self,
        datatype: DataType[T],
        mode=AttrMode.READ_WRITE,
        handler: Handler | None = None,
    ) -> None:
        super().__init__(datatype, mode=mode, handler=handler)  # type: ignore

    async def process(self, value: T) -> None:
        await self.set(value)

        await super().process(value)  # type: ignore
