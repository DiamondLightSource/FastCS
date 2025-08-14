from __future__ import annotations

import asyncio
from collections.abc import Callable
from enum import Enum
from typing import Any, Generic

import fastcs

from .datatypes import ATTRIBUTE_TYPES, AttrCallback, DataType, T

ONCE = float("inf")
"""Special value to indicate that an attribute should be updated once on start up."""


class AttrMode(Enum):
    """Access mode of an ``Attribute``."""

    READ = 1
    WRITE = 2
    READ_WRITE = 3


class _BaseAttrHandler:
    async def initialise(self, controller: fastcs.controller.BaseController) -> None:
        pass


class AttrHandlerW(_BaseAttrHandler):
    """Protocol for setting the value of an ``Attribute``."""

    async def put(self, attr: AttrW[T], value: T) -> None:
        pass


class AttrHandlerR(_BaseAttrHandler):
    """Protocol for updating the cached readback value of an ``Attribute``."""

    # If update period is None then the attribute will not be updated as a task.
    update_period: float | None = None

    async def update(self, attr: AttrR[T]) -> None:
        pass


class AttrHandlerRW(AttrHandlerR, AttrHandlerW):
    """Protocol encapsulating both ``AttrHandlerR`` and ``AttHandlerW``."""

    pass


class SimpleAttrHandler(AttrHandlerRW):
    """Handler for internal parameters"""

    async def put(self, attr: AttrW[T], value: T) -> None:
        await attr.update_display_without_process(value)

        if isinstance(attr, AttrRW):
            await attr.set(value)

    async def update(self, attr: AttrR) -> None:
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
        description: str | None = None,
    ) -> None:
        assert issubclass(datatype.dtype, ATTRIBUTE_TYPES), (
            f"Attr type must be one of {ATTRIBUTE_TYPES}, "
            "received type {datatype.dtype}"
        )
        self._datatype: DataType[T] = datatype
        self._access_mode: AttrMode = access_mode
        self._group = group
        self._handler = handler
        self.enabled = True
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

    async def initialise(self, controller: fastcs.controller.BaseController) -> None:
        if self._handler is not None:
            await self._handler.initialise(controller)

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
        handler: AttrHandlerR | None = None,
        initial_value: T | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            access_mode,
            group,
            handler,
            description=description,
        )
        self._value: T = (
            datatype.initial_value if initial_value is None else initial_value
        )
        self._update_callbacks: list[AttrCallback[T]] | None = None
        self._updater = handler

    def get(self) -> T:
        return self._value

    async def set(self, value: T) -> None:
        self._value = self._datatype.validate(value)

        if self._update_callbacks is not None:
            await asyncio.gather(*[cb(self._value) for cb in self._update_callbacks])

    def add_update_callback(self, callback: AttrCallback[T]) -> None:
        if self._update_callbacks is None:
            self._update_callbacks = []
        self._update_callbacks.append(callback)

    @property
    def updater(self) -> AttrHandlerR | None:
        return self._updater


class AttrW(Attribute[T]):
    """A write-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.WRITE,
        group: str | None = None,
        handler: AttrHandlerW | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            access_mode,
            group,
            handler,
            description=description,
        )
        self._process_callbacks: list[AttrCallback[T]] | None = None
        self._write_display_callbacks: list[AttrCallback[T]] | None = None
        self._setter = handler

    async def process(self, value: T) -> None:
        await self.process_without_display_update(value)
        await self.update_display_without_process(value)

    async def process_without_display_update(self, value: T) -> None:
        value = self._datatype.validate(value)
        if self._process_callbacks:
            await asyncio.gather(*[cb(value) for cb in self._process_callbacks])

    async def update_display_without_process(self, value: T) -> None:
        value = self._datatype.validate(value)
        if self._write_display_callbacks:
            await asyncio.gather(*[cb(value) for cb in self._write_display_callbacks])

    def add_process_callback(self, callback: AttrCallback[T]) -> None:
        if self._process_callbacks is None:
            self._process_callbacks = []
        self._process_callbacks.append(callback)

    def has_process_callback(self) -> bool:
        return bool(self._process_callbacks)

    def add_write_display_callback(self, callback: AttrCallback[T]) -> None:
        if self._write_display_callbacks is None:
            self._write_display_callbacks = []
        self._write_display_callbacks.append(callback)

    @property
    def sender(self) -> AttrHandlerW | None:
        return self._setter


class AttrRW(AttrR[T], AttrW[T]):
    """A read-write ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        access_mode=AttrMode.READ_WRITE,
        group: str | None = None,
        handler: AttrHandlerRW | None = None,
        initial_value: T | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            access_mode,
            group=group,
            handler=handler if handler else SimpleAttrHandler(),
            initial_value=initial_value,
            description=description,
        )

    async def process(self, value: T) -> None:
        await self.set(value)

        await super().process(value)  # type: ignore
