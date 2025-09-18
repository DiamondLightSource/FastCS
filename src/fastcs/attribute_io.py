from typing import Generic

from fastcs.attributes import AttrR, AttrRW
from fastcs.attribute_io_ref import AttributeIORef, AttributeIORefT
from fastcs.datatypes import T


class AttributeIO(Generic[T, AttributeIORefT]):
    def __init__(self, io_ref: type[AttributeIORefT]):
        self.ref = io_ref

    async def update(self, attr: AttrR[T]) -> None:
        raise NotImplementedError()

    async def send(
        self, attr: AttrRW[T], value # TODO, type this
    ) -> None:
        raise NotImplementedError()


AnyAttributeIO = AttributeIO[T, AttributeIORef]
