from dataclasses import dataclass

from fastcs.datatypes._numeric import _Numeric


@dataclass(frozen=True)
class Int(_Numeric[int]):
    """`DataType` mapping to builtin ``int``."""

    @property
    def dtype(self) -> type[int]:
        return int
