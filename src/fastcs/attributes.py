from __future__ import annotations

from collections.abc import Callable
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

    # If update period is None then the attribute will not be updated as a task.
    update_period: float | None = None

    async def update(self, controller: Any, attr: AttrR) -> None:
        pass


@runtime_checkable
class Handler(Sender, Updater, Protocol):
    """Protocol encapsulating both ``Sender`` and ``Updater``."""

    pass


class SimpleHandler(Handler):
    """Handler for internal parameters"""

    async def put(self, controller: Any, attr: AttrW, value: Any):
        await attr.update_display_without_process(value)

        if isinstance(attr, AttrRW):
            await attr.set(value)

    async def update(self, controller: Any, attr: AttrR):
        raise RuntimeError("SimpleHandler cannot update")


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
        allowed_values: list[T] | None = None,
        description: str | None = None,
    ) -> None:
        assert (
            datatype.dtype in ATTRIBUTE_TYPES
        ), f"Attr type must be one of {ATTRIBUTE_TYPES}, received type {datatype.dtype}"
        self._datatype: DataType[T] = datatype
        self._access_mode: AttrMode = access_mode
        self._group = group
        self.enabled = True
        self._allowed_values: list[T] | None = allowed_values
        self.description = description

        # A callback to use when setting the datatype to a different value, for example
        # changing the units on an int. This should be implemented in the backend.
        self._update_datatype_callbacks: list[Callable[[DataType[T]], None]] = []

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

    @property
    def allowed_values(self) -> list[T] | None:
        return self._allowed_values

    def add_update_datatype_callback(
        self, callback: Callable[[DataType[T]], None]
    ) -> None:
        self._update_datatype_callbacks.append(callback)

    def update_datatype(self, datatype: DataType[T]) -> None:
        if not isinstance(self._datatype, type(datatype)):
            raise ValueError(
                f"Attribute datatype must be of type {type(self._datatype)}"
            )
        self._datatype = datatype
        for callback in self._update_datatype_callbacks:
            callback(datatype)


class AttrR(Attribute[T]):
    """A read-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.READ,
        group: str | None = None,
        handler: Updater | None = None,
        initial_value: T | None = None,
        allowed_values: list[T] | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            access_mode,
            group,
            handler,
            allowed_values=allowed_values,  # type: ignore
            description=description,
        )
        self._value: T = (
            datatype.initial_value if initial_value is None else initial_value
        )
        self._update_callback: AttrCallback[T] | None = None
        self._updater = handler

    def get(self) -> T:
        return self._value

    async def set(self, value: T) -> None:
        self._value = self._datatype.validate(value)

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
        allowed_values: list[T] | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            access_mode,
            group,
            handler,
            allowed_values=allowed_values,  # type: ignore
            description=description,
        )
        self._process_callback: AttrCallback[T] | None = None
        self._write_display_callback: AttrCallback[T] | None = None

        if handler is not None:
            self._sender = handler
        else:
            self._sender = SimpleHandler()

    async def process(self, value: T) -> None:
        await self.process_without_display_update(value)
        await self.update_display_without_process(value)

    async def process_without_display_update(self, value: T) -> None:
        if self._process_callback is not None:
            await self._process_callback(self._datatype.validate(value))

    async def update_display_without_process(self, value: T) -> None:
        if self._write_display_callback is not None:
            await self._write_display_callback(self._datatype.validate(value))

    def set_process_callback(self, callback: AttrCallback[T] | None) -> None:
        self._process_callback = callback

    def has_process_callback(self) -> bool:
        return self._process_callback is not None

    def set_write_display_callback(self, callback: AttrCallback[T] | None) -> None:
        self._write_display_callback = callback

    @property
    def sender(self) -> Sender:
        return self._sender


class AttrRW(AttrR[T], AttrW[T]):
    """A read-write ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.READ_WRITE,
        group: str | None = None,
        handler: Handler | None = None,
        initial_value: T | None = None,
        allowed_values: list[T] | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            access_mode,
            group=group,
            handler=handler,
            initial_value=initial_value,
            allowed_values=allowed_values,  # type: ignore
            description=description,
        )

    async def process(self, value: T) -> None:
        await self.set(value)

        await super().process(value)  # type: ignore
