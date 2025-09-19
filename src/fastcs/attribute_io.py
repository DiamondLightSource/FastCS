from typing import Generic

from fastcs.attribute_io_ref import AttributeIORef, AttributeIORefT
from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import T


class AttributeIO(Generic[T, AttributeIORefT]):
    def __init__(self, io_ref: type[AttributeIORefT]):
        self.ref_type = io_ref

    async def update(self, attr: AttrR[T]) -> None:
        raise NotImplementedError()

    async def send(
        self,
        attr: AttrRW[T],
        value,  # TODO, type this
    ) -> None:
        raise NotImplementedError()


class SimpleAttributeIO(AttributeIO):
    """IO for internal parameters"""

    async def send(self, attr: AttrRW[T], value) -> None:
        await attr.update_display_without_process(value)

        if isinstance(attr, AttrRW):
            await attr.set(value)

    async def update(self, attr: AttrR[T]) -> None:
        raise RuntimeError("SimpleAttributeIO can't update")


AnyAttributeIO = AttributeIO[T, AttributeIORef]
