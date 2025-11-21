from fastcs.attributes.attr_r import AttrR
from fastcs.attributes.attr_w import AttrW
from fastcs.attributes.attribute_io_ref import AttributeIORefT
from fastcs.datatypes import DataType, DType_T
from fastcs.logging import bind_logger

logger = bind_logger(logger_name=__name__)


class AttrRW(AttrR[DType_T, AttributeIORefT], AttrW[DType_T, AttributeIORefT]):
    """A read-write ``Attribute``."""

    def __init__(
        self,
        datatype: DataType[DType_T],
        io_ref: AttributeIORefT | None = None,
        group: str | None = None,
        initial_value: DType_T | None = None,
        description: str | None = None,
    ):
        super().__init__(datatype, io_ref, group, initial_value, description)

        self._setpoint_initialised = False

        if io_ref is None:
            self.set_on_put_callback(self._internal_update)

    async def _internal_update(
        self, attr: AttrW[DType_T, AttributeIORefT], value: DType_T
    ):
        """Update value directly when Attribute has no IO"""
        assert attr is self
        await self.update(value)

    async def update(self, value: DType_T):
        await super().update(value)

        if not self._setpoint_initialised:
            await self._call_sync_setpoint_callbacks(value)
            self._setpoint_initialised = True
