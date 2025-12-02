import enum
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import numpy as np
from numpy.typing import DTypeLike

DType_T = TypeVar(
    "DType_T",
    int,  # Int
    float,  # Float
    bool,  # Bool
    str,  # String
    enum.Enum,  # Enum
    np.ndarray,  # Waveform
    list[tuple[str, DTypeLike]],  # Table
)
"""A builtin (or numpy) type supported by a corresponding FastCS Attribute DataType"""

DATATYPE_DTYPES: tuple[type] = DType_T.__constraints__  # type: ignore


@dataclass(frozen=True)
class DataType(Generic[DType_T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    @property
    @abstractmethod
    def dtype(self) -> type[DType_T]:  # Using property due to lack of Generic ClassVars
        raise NotImplementedError()

    def validate(self, value: Any) -> DType_T:
        """Validate a value against the datatype.

        The base implementation is to try the cast and raise a useful error if it fails.

        Child classes can implement logic before calling ``super.validate(value)`` to
        modify the value passed in and help the cast succeed or after to perform further
        validation of the coerced type.

        Args:
            value: The value to validate

        Returns:
            The validated value

        Raises:
            ValueError: If the value cannot be coerced

        """
        if isinstance(value, self.dtype):
            return value

        try:
            return self.dtype(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to cast {value} to type {self.dtype}") from e

    @property
    @abstractmethod
    def initial_value(self) -> DType_T:
        raise NotImplementedError()
