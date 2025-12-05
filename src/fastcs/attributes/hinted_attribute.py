from dataclasses import dataclass

from fastcs.attributes.attribute import Attribute
from fastcs.datatypes import DType


@dataclass(kw_only=True)
class HintedAttribute:
    """An `Attribute` type hint found on a `Controller` class

    e.g. ``attr: AttrR[int]``

    """

    attr_type: type[Attribute]
    """The type of the `Attribute` in the type hint - e.g. `AttrR`"""
    dtype: type[DType] | None
    """The dtype of the `Attribute` in the type hint, if any - e.g. `int`"""
