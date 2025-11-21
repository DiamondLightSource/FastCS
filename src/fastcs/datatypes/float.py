from dataclasses import dataclass
from typing import Any

from fastcs.datatypes._numerical import _Numerical


@dataclass(frozen=True)
class Float(_Numerical[float]):
    """`DataType` mapping to builtin ``float``."""

    prec: int = 2

    @property
    def dtype(self) -> type[float]:
        return float

    def validate(self, value: Any) -> float:
        _value = super().validate(value)

        if self.prec is not None:
            _value = round(_value, self.prec)

        return _value
