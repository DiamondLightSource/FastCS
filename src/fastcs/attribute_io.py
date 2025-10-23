from typing import Any, Generic, cast, get_args

from fastcs.attribute_io_ref import AttributeIORef, AttributeIORefT
from fastcs.attributes import AttrR, AttrW
from fastcs.datatypes import T
from fastcs.tracer import Tracer


class AttributeIO(Generic[T, AttributeIORefT], Tracer):
    """Base class for performing IO for an ``Attribute``

    This class should be inherited to implement reading and writing values from
    ``Attributes`` via some API. For read, ``Attribute``s implement the ``update``
    method and for write, ``Attribute`` implement the ``send`` method.

    Concrete implementations of this class must be parameterised with a specific
    ``AttributeIORef`` that defines exactly what part of the API the ``Attribute``
    corresponds to. See the docstring for ``AttributeIORef`` for more information.
    """

    ref_type = AttributeIORef

    def __init_subclass__(cls) -> None:
        # sets ref_type from subclass generic args
        # from python 3.12 we can use types.get_original_bases
        args = get_args(cast(Any, cls).__orig_bases__[0])
        cls.ref_type = args[1]

    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[T, AttributeIORefT]) -> None:
        raise NotImplementedError()

    async def send(self, attr: AttrW[T, AttributeIORefT], value: T) -> None:
        raise NotImplementedError()


AnyAttributeIO = AttributeIO[T, AttributeIORef]
