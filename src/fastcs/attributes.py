from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Protocol, runtime_checkable

from .datatypes import ATTRIBUTE_TYPES, AttrCallback, DataType, T


class AttrMode(Enum):
    """Access mode of an ``Attribute``."""

    READ = 1
    WRITE = 2
    READ_WRITE = 3


@runtime_checkable
class Sender(Protocol):
    """Protocol for setting the value of an ``Attribute``."""

    async def put(self, controller: Any, attr: AttrW, value: Any) -> None:
        pass


@runtime_checkable
class Updater(Protocol):
    """Protocol for updating the cached readback value of an ``Attribute``."""

    update_period: float

    async def update(self, controller: Any, attr: AttrR) -> None:
        pass


@runtime_checkable
class Handler(Sender, Updater, Protocol):
    """Protocol encapsulating both ``Sender`` and ``Updater``."""

    pass


class Attribute(Generic[T]):
    """Base FastCS attribute.

    Instances of this class added to a ``Controller`` will be used by the backend.
    """

    def __init__(
        self,
        datatype: DataType[T],
        access_mode: AttrMode,
        group: str | None = None,
        handler: Any = None,
    ) -> None:
        assert (
            datatype.dtype in ATTRIBUTE_TYPES
        ), f"Attr type must be one of {ATTRIBUTE_TYPES}, received type {datatype.dtype}"
        self._datatype: DataType[T] = datatype
        self._access_mode: AttrMode = access_mode
        self._group = group

    @property
    def datatype(self) -> DataType[T]:
        return self._datatype

    @property
    def dtype(self) -> type[T]:
        return self._datatype.dtype

    @property
    def access_mode(self) -> AttrMode:
        return self._access_mode

    @property
    def group(self) -> str | None:
        return self._group


class AttrR(Attribute[T]):
    """A read-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.READ,
        group: str | None = None,
        handler: Updater | None = None,
    ) -> None:
        super().__init__(datatype, access_mode, group, handler)  # type: ignore
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
    """A write-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.WRITE,
        group: str | None = None,
        handler: Sender | None = None,
        allowed_values: list[str] | None = None,
    ) -> None:
        super().__init__(datatype, access_mode, group, handler)  # type: ignore
        self._process_callback: AttrCallback[T] | None = None
        self._write_display_callback: AttrCallback[T] | None = None
        self._sender = handler

        self._allowed_values = allowed_values

    @property
    def allowed_values(self) -> list[str] | None:
        return self._allowed_values

    async def process(self, value: T) -> None:
        await self.process_without_display_update(value)
        await self.update_display_without_process(value)

    async def process_without_display_update(self, value: T) -> None:
        if self._process_callback is not None:
            await self._process_callback(self._datatype.dtype(value))

    async def update_display_without_process(self, value: T) -> None:
        if self._write_display_callback is not None:
            await self._write_display_callback(self._datatype.dtype(value))

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
    """A read-write ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.READ_WRITE,
        group: str | None = None,
        handler: Handler | None = None,
        allowed_values: list[str] | None = None,
    ) -> None:
        super().__init__(datatype, access_mode, group, handler, allowed_values)  # type: ignore

    async def process(self, value: T) -> None:
        await self.set(value)

        await super().process(value)  # type: ignore
