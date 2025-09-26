from typing import Any, Generic, cast, get_args

from fastcs.attribute_io_ref import AttributeIORef, AttributeIORefT
from fastcs.attributes import AttrR, AttrRW
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


AnyAttributeIO = AttributeIO[AttributeIORef, T]
