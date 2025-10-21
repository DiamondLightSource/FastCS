from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Generic

from fastcs.attribute_io_ref import AttributeIORefT
from fastcs.datatypes import (
    ATTRIBUTE_TYPES,
    AttrSetCallback,
    AttrUpdateCallback,
    DataType,
    T,
)
from fastcs.tracer import Tracer

ONCE = float("inf")
"""Special value to indicate that an attribute should be updated once on start up."""


class Attribute(Generic[T, AttributeIORefT], Tracer):
    """Base FastCS attribute.

    Instances of this class added to a ``Controller`` will be used by the FastCS class.
    """

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefT | None = None,
        group: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__()

        assert issubclass(datatype.dtype, ATTRIBUTE_TYPES), (
            f"Attr type must be one of {ATTRIBUTE_TYPES}, "
            "received type {datatype.dtype}"
        )
        self._io_ref = io_ref
        self._datatype: DataType[T] = datatype
        self._group = group
        self.enabled = True
        self.description = description

        # A callback to use when setting the datatype to a different value, for example
        # changing the units on an int. This should be implemented in the backend.
        self._update_datatype_callbacks: list[Callable[[DataType[T]], None]] = []

        # Name to be filled in by Controller when the Attribute is bound
        self._name = None

    @property
    def io_ref(self) -> AttributeIORefT:
        if self._io_ref is None:
            raise RuntimeError(f"{self} has no AttributeIORef")
        return self._io_ref

    def has_io_ref(self):
        return self._io_ref is not None

    @property
    def datatype(self) -> DataType[T]:
        return self._datatype

    @property
    def dtype(self) -> type[T]:
        return self._datatype.dtype

    @property
    def group(self) -> str | None:
        return self._group

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

    def set_name(self, name: list[str]):
        if self._name:
            raise ValueError(
                f"Attribute is already registered with a controller as {self._name}"
            )

        self._name = name

    def __repr__(self):
        return f"{self.__class__.__name__}({self._name}, {self._datatype})"


class AttrR(Attribute[T, AttributeIORefT]):
    """A read-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefT | None = None,
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
        self._on_set_callbacks: list[AttrSetCallback[T]] | None = None
        self._on_update_callbacks: list[AttrUpdateCallback] | None = None

    def get(self) -> T:
        return self._value

    async def set(self, value: T) -> None:
        self.log_event("Attribute set", attribute=self, value=value)

        self._value = self._datatype.validate(value)

        if self._on_set_callbacks is not None:
            await asyncio.gather(*[cb(self._value) for cb in self._on_set_callbacks])

    def add_set_callback(self, callback: AttrSetCallback[T]) -> None:
        if self._on_set_callbacks is None:
            self._on_set_callbacks = []
        self._on_set_callbacks.append(callback)

    def add_update_callback(self, callback: AttrUpdateCallback):
        if self._on_update_callbacks is None:
            self._on_update_callbacks = []
        self._on_update_callbacks.append(callback)

    async def update(self):
        if self._on_update_callbacks is not None:
            await asyncio.gather(*[cb() for cb in self._on_update_callbacks])


class AttrW(Attribute[T, AttributeIORefT]):
    """A write-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefT | None = None,
        group: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            datatype,  # type: ignore
            io_ref,
            group,
            description=description,
        )
        self._process_callbacks: list[AttrSetCallback[T]] | None = None
        self._write_display_callbacks: list[AttrSetCallback[T]] | None = None

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

    def add_process_callback(self, callback: AttrSetCallback[T]) -> None:
        if self._process_callbacks is None:
            self._process_callbacks = []
        self._process_callbacks.append(callback)

    def has_process_callback(self) -> bool:
        return bool(self._process_callbacks)

    def add_write_display_callback(self, callback: AttrSetCallback[T]) -> None:
        if self._write_display_callbacks is None:
            self._write_display_callbacks = []
        self._write_display_callbacks.append(callback)


class AttrRW(AttrR[T, AttributeIORefT], AttrW[T, AttributeIORefT]):
    """A read-write ``Attribute``."""

    async def process(self, value: T) -> None:
        await self.set(value)

        await super().process(value)  # type: ignore
