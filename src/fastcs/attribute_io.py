from typing import Generic, get_args

from fastcs.attribute_io_ref import AttributeIORef, AttributeIORefT
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import T


class AttributeIO(Generic[T, AttributeIORefT]):
    def __init_subclass__(cls) -> None:
        # sets ref_type from subclass generic args
        args = get_args(cls.__orig_bases__[0])
        cls.ref_type = args[1]

    async def update(self, attr: AttrR[T]) -> None:
        raise NotImplementedError()

    async def send(
        self,
        attr: AttrRW[T],
        value,  # TODO, type this
    ) -> None:
        raise NotImplementedError()


class SimpleAttributeIO(AttributeIO[T, AttributeIORef]):
    """IO for internal parameters"""

    async def send(self, attr: AttrW[T], value) -> None:
        await attr.update_display_without_process(value)

        if isinstance(attr, AttrRW):
            await attr.set(value)

    async def update(self, attr: AttrR[T]) -> None:
        raise RuntimeError("SimpleAttributeIO can't update")


AnyAttributeIO = AttributeIO[T, AttributeIORef]
