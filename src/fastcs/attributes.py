from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Generic

from fastcs.attribute_io_ref import AttributeIORefT
from fastcs.datatypes import ATTRIBUTE_TYPES, DataType, T
from fastcs.logging import bind_logger
from fastcs.tracer import Tracer

ONCE = float("inf")
"""Special value to indicate that an attribute should be updated once on start up."""

logger = bind_logger(logger_name=__name__)


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
        # changing the units on an int.
        self._update_datatype_callbacks: list[Callable[[DataType[T]], None]] = []

        # Path and name to be filled in by Controller it is bound to
        self._name = ""
        self._path = []

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

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> list[str]:
        return self._path

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

    def set_name(self, name: str):
        if self._name:
            raise RuntimeError(
                f"Attribute is already registered with a controller as {self._name}"
            )

        self._name = name

    def set_path(self, path: list[str]):
        if self._path:
            raise RuntimeError(
                f"Attribute is already registered with a controller at {self._path}"
            )

        self._path = path

    def __repr__(self):
        name = self.__class__.__name__
        path = ".".join(self._path + [self._name]) or None
        datatype = self._datatype.__class__.__name__

        return f"{name}(path={path}, datatype={datatype}, io_ref={self._io_ref})"


AttrIOUpdateCallback = Callable[["AttrR[T, Any]"], Awaitable[None]]
"""An AttributeIO callback that takes an AttrR and updates its value"""
AttrUpdateCallback = Callable[[], Awaitable[None]]
"""A callback to be called periodically to update an attribute"""
AttrOnUpdateCallback = Callable[[T], Awaitable[None]]
"""A callback to be called when the value of the attribute is updated"""


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
        super().__init__(datatype, io_ref, group, description=description)
        self._value: T = (
            datatype.initial_value if initial_value is None else initial_value
        )
        self._update_callback: AttrIOUpdateCallback[T] | None = None
        """Callback to update the value of the attribute with an IO to the source"""
        self._on_update_callbacks: list[AttrOnUpdateCallback[T]] | None = None
        """Callbacks to publish changes to the value of the attribute"""

    def get(self) -> T:
        """Get the cached value of the attribute."""
        return self._value

    async def update(self, value: T) -> None:
        """Update the value of the attibute

        This sets the cached value of the attribute presented in the API. It should
        generally only be called from an IO or a controller that is updating the value
        from some underlying source.

        To request a change to the setpoint of the attribute, use the ``put`` method,
        which will attempt to apply the change to the underlying source.

        """
        self.log_event("Attribute set", attribute=self, value=value)

        self._value = self._datatype.validate(value)

        if self._on_update_callbacks is not None:
            try:
                await asyncio.gather(
                    *[cb(self._value) for cb in self._on_update_callbacks]
                )
            except Exception as e:
                logger.opt(exception=e).error(
                    "On update callback failed", attribute=self, value=value
                )
                raise

    def add_on_update_callback(self, callback: AttrOnUpdateCallback[T]) -> None:
        """Add a callback to be called when the value of the attribute is updated

        The callback will be called with the updated value.

        """
        if self._on_update_callbacks is None:
            self._on_update_callbacks = []
        self._on_update_callbacks.append(callback)

    def set_update_callback(self, callback: AttrIOUpdateCallback[T]):
        """Set the callback to update the value of the attribute from the source

        The callback will be converted to an async task and called periodically.

        """
        if self._update_callback is not None:
            raise RuntimeError("Attribute already has an IO update callback")

        self._update_callback = callback

    def bind_update_callback(self) -> AttrUpdateCallback:
        """Bind self into the registered IO update callback"""
        if self._update_callback is None:
            raise RuntimeError("Attribute has no update callback")
        else:
            update_callback = self._update_callback

        async def update_attribute():
            try:
                self.log_event("Update attribute", topic=self)
                await update_callback(self)
            except Exception as e:
                logger.opt(exception=e).error("Update loop failed", attribute=self)
                raise

        return update_attribute


AttrOnPutCallback = Callable[["AttrW[T, Any]", T], Awaitable[None]]
"""Callbacks to be called when the setpoint of an attribute is changed"""
AttrSyncSetpointCallback = Callable[[T], Awaitable[None]]
"""Callbacks to be called when the setpoint of an attribute is changed"""


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
        self._on_put_callback: AttrOnPutCallback[T] | None = None
        """Callback to action a change to the setpoint of the attribute"""
        self._sync_setpoint_callbacks: list[AttrSyncSetpointCallback[T]] = []
        """Callbacks to publish changes to the setpoint of the attribute"""

    async def put(self, setpoint: T, sync_setpoint: bool = False) -> None:
        """Set the setpoint of the attribute

        This should be called by clients to the attribute such as transports to apply a
        change to the attribute. The ``_on_put_callback`` will be called with this new
        setpoint, which may or may not take effect depending on the validity of the new
        value. For example, if the attribute has an IO to some device, the value might
        be rejected.

        To directly change the value of the attribute, for example from an update loop
        that has read a new value from some underlying source, call the ``update``
        method.

        """
        setpoint = self._datatype.validate(setpoint)
        if self._on_put_callback is not None:
            try:
                await self._on_put_callback(self, setpoint)
            except Exception as e:
                logger.opt(exception=e).error(
                    "Put failed", attribute=self, setpoint=setpoint
                )

        if sync_setpoint:
            try:
                await self._call_sync_setpoint_callbacks(setpoint)
            except Exception as e:
                logger.opt(exception=e).error(
                    "Sync setpoint failed", attribute=self, setpoint=setpoint
                )

    async def _call_sync_setpoint_callbacks(self, setpoint: T) -> None:
        if self._sync_setpoint_callbacks:
            await asyncio.gather(
                *[cb(setpoint) for cb in self._sync_setpoint_callbacks]
            )

    def set_on_put_callback(self, callback: AttrOnPutCallback[T]) -> None:
        """Set the callback to call when the setpoint is changed

        The callback will be called with the attribute and the new setpoint.

        """
        if self._on_put_callback is not None:
            raise RuntimeError("Attribute already has an on put callback")

        self._on_put_callback = callback

    def add_sync_setpoint_callback(self, callback: AttrSyncSetpointCallback[T]) -> None:
        """Add a callback to publish changes to the setpoint of the attribute

        The callback will be called with the new setpoint.

        """
        self._sync_setpoint_callbacks.append(callback)


class AttrRW(AttrR[T, AttributeIORefT], AttrW[T, AttributeIORefT]):
    """A read-write ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[T],
        io_ref: AttributeIORefT | None = None,
        group: str | None = None,
        initial_value: T | None = None,
        description: str | None = None,
    ):
        super().__init__(datatype, io_ref, group, initial_value, description)

        self._setpoint_initialised = False

        if io_ref is None:
            self.set_on_put_callback(self._internal_update)

    async def _internal_update(self, attr: AttrW[T, AttributeIORefT], value: T):
        """Update value directly when Attribute has no IO"""
        assert attr is self
        await self.update(value)

    async def update(self, value: T):
        await super().update(value)

        if not self._setpoint_initialised:
            await self._call_sync_setpoint_callbacks(value)
            self._setpoint_initialised = True
