from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import DTypeLike

from fastcs.datatypes.datatype import DataType


@dataclass(frozen=True)
class Table(DataType[np.ndarray]):
    # https://numpy.org/devdocs/user/basics.rec.html#structured-datatype-creation
    structured_dtype: list[tuple[str, DTypeLike]]

    @property
    def dtype(self) -> type[np.ndarray]:
        return np.ndarray

    @property
    def initial_value(self) -> np.ndarray:
        return np.array([], dtype=self.structured_dtype)

    def validate(self, value: Any) -> np.ndarray:
        _value = super().validate(value)

        if self.structured_dtype != _value.dtype:
            raise ValueError(
                f"Value dtype {_value.dtype.descr} is not the same as the structured "
                f"dtype {self.structured_dtype}"
            )

        return _value

    @staticmethod
    def equal(value1: np.ndarray, value2: np.ndarray) -> bool:
        return np.array_equal(value1, value2)
