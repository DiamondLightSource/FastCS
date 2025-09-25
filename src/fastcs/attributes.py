from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Generic, Self

from typing_extensions import TypeVar

import fastcs
from fastcs.attribute_io_ref import AttributeIORef

from .datatypes import ATTRIBUTE_TYPES, AttrCallback, DataType, T

# TODO rename this: typevar with default
AttributeIORefTD = TypeVar(
    "AttributeIORefTD", bound=AttributeIORef, default=AttributeIORef, covariant=True
)

ONCE = float("inf")
"""Special value to indicate that an attribute should be updated once on start up."""


class Attribute(Generic[T, AttributeIORefTD]):
    """Base FastCS attribute.

    Instances of this class added to a ``Controller`` will be used by the backend.
    """

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefTD | None = None,
        group: str | None = None,
        description: str | None = None,
    ) -> None:
        assert issubclass(datatype.dtype, ATTRIBUTE_TYPES), (
            f"Attr type must be one of {ATTRIBUTE_TYPES}, "
            "received type {datatype.dtype}"
        )
        self.io_ref = io_ref or AttributeIORef()
        self._datatype: DataType[T] = datatype
        self._group = group
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
    def group(self) -> str | None:
        return self._group

    async def initialise(self, controller: fastcs.controller.BaseController) -> None:
        pass

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


class AttrR(Attribute[T, AttributeIORefTD]):
    """A read-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefTD | None = None,
        group: str | None = None,
        initial_value: T | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            io_ref,
            group,
            description=description,
        )
        self._value: T = (
            datatype.initial_value if initial_value is None else initial_value
        )
        self._on_set_callbacks: list[AttrCallback[T]] | None = None
        self._on_update_callbacks: list[AttrCallback[T]] | None = None

    def get(self) -> T:
        return self._value

    async def set(self, value: T) -> None:
        self._value = self._datatype.validate(value)

        if self._on_set_callbacks is not None:
            await asyncio.gather(*[cb(self._value) for cb in self._on_set_callbacks])

    def add_set_callback(self, callback: AttrCallback[T]) -> None:
        if self._on_set_callbacks is None:
            self._on_set_callbacks = []
        self._on_set_callbacks.append(callback)

    def add_update_callback(
        self, callback: Callable[[Self], Coroutine[None, None, None]]
    ):
        if self._on_update_callbacks is None:
            self._on_update_callbacks = []
        self._on_update_callbacks.append(callback)

    async def update(self):
        if self._on_update_callbacks is not None:
            await asyncio.gather(*[cb(self) for cb in self._on_update_callbacks])


class AttrW(Attribute[T, AttributeIORefTD]):
    """A write-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefTD | None = None,
        group: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            io_ref,
            group,
            description=description,
        )
        self._process_callbacks: list[AttrCallback[T]] | None = None
        self._write_display_callbacks: list[AttrCallback[T]] | None = None

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

    async def put(self, value):
        await self.io_ref.send(self, value)


class AttrRW(AttrR[T, AttributeIORefTD], AttrW[T, AttributeIORefTD]):
    """A read-write ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefTD | None = None,
        group: str | None = None,
        initial_value: T | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            io_ref,
            group=group,
            initial_value=initial_value,
            description=description,
        )

    async def process(self, value: T) -> None:
        await self.set(value)

        await super().process(value)  # type: ignore
