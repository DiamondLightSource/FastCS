from dataclasses import dataclass

from fastcs.datatypes._numerical import _Numerical


@dataclass(frozen=True)
class Int(_Numerical[int]):
    """`DataType` mapping to builtin ``int``."""

    @property
    def dtype(self) -> type[int]:
        return int
