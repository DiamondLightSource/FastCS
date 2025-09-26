from typing import Any, Generic, cast, get_args

from fastcs.attribute_io_ref import AttributeIORef, AttributeIORefT
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import T


class AttributeIO(Generic[AttributeIORefT, T]):
    def __init_subclass__(cls) -> None:
        # sets ref_type from subclass generic args
        # from python 3.12 we can use types.get_original_bases
        args = get_args(cast(Any, cls).__orig_bases__[0])
        cls.ref_type = args[0]

    async def update(self, attr: AttrR[T, AttributeIORefT]) -> None:
        raise NotImplementedError()

    async def send(
        self,
        attr: AttrRW[T, AttributeIORefT],
        value,  # TODO, type this
    ) -> None:
        raise NotImplementedError()


class SimpleAttributeIO(AttributeIO[AttributeIORef, T]):
    """IO for internal parameters"""

    async def send(self, attr: AttrW[T, AttributeIORefT], value) -> None:
        await attr.update_display_without_process(value)

        if isinstance(attr, AttrRW):
            await attr.set(value)

    async def update(self, attr: AttrR[T, AttributeIORefT]) -> None:
        raise RuntimeError("SimpleAttributeIO can't update")


AnyAttributeIO = AttributeIO[AttributeIORef, T]
