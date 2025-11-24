from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastcs.attributes.attribute import Attribute
from fastcs.attributes.attribute_io_ref import AttributeIORefT
from fastcs.datatypes import DataType, DType_T
from fastcs.logging import bind_logger

logger = bind_logger(logger_name=__name__)


AttrIOUpdateCallback = Callable[["AttrR[DType_T, Any]"], Awaitable[None]]
"""An AttributeIO callback that takes an AttrR and updates its value"""
AttrUpdateCallback = Callable[[], Awaitable[None]]
"""A callback to be called periodically to update an attribute"""
AttrOnUpdateCallback = Callable[[DType_T], Awaitable[None]]
"""A callback to be called when the value of the attribute is updated"""


class AttrR(Attribute[DType_T, AttributeIORefT]):
    """A read-only ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[DType_T],
        io_ref: AttributeIORefT | None = None,
        group: str | None = None,
        initial_value: DType_T | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(datatype, io_ref, group, description=description)
        self._value: DType_T = (
            datatype.initial_value if initial_value is None else initial_value
        )
        self._update_callback: AttrIOUpdateCallback[DType_T] | None = None
        """Callback to update the value of the attribute with an IO to the source"""
        self._on_update_callbacks: list[AttrOnUpdateCallback[DType_T]] | None = None
        """Callbacks to publish changes to the value of the attribute"""

    def get(self) -> DType_T:
        """Get the cached value of the attribute."""
        return self._value

    async def update(self, value: DType_T) -> None:
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

    def add_on_update_callback(self, callback: AttrOnUpdateCallback[DType_T]) -> None:
        """Add a callback to be called when the value of the attribute is updated

        The callback will be called with the updated value.

        """
        if self._on_update_callbacks is None:
            self._on_update_callbacks = []
        self._on_update_callbacks.append(callback)

    def set_update_callback(self, callback: AttrIOUpdateCallback[DType_T]):
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
