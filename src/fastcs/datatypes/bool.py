from dataclasses import dataclass

from fastcs.datatypes.datatype import DataType


@dataclass(frozen=True)
class Bool(DataType[bool]):
    """`DataType` mapping to builtin ``bool``."""

    @property
    def dtype(self) -> type[bool]:
        return bool

    @property
    def initial_value(self) -> bool:
        return False
