from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T_Numerical = TypeVar("T_Numerical", int, float)
T = TypeVar("T", int, float, bool, str)
ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


@dataclass(frozen=True)  # So that we can type hint with dataclass methods
class DataType(Generic[T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    @property
    @abstractmethod
    def dtype(self) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass

    def validate(self, value: T) -> T:
        """Validate a value against fields in the datatype."""
        return value

    @property
    def initial_value(self) -> T:
        return self.dtype()


@dataclass(frozen=True)
class _Numerical(DataType[T_Numerical]):
    units: str | None = None
    min: int | None = None
    max: int | None = None
    min_alarm: int | None = None
    max_alarm: int | None = None

    def validate(self, value: T_Numerical) -> T_Numerical:
        if self.min is not None and value < self.min:
            raise ValueError(f"Value {value} is less than minimum {self.min}")
        if self.max is not None and value > self.max:
            raise ValueError(f"Value {value} is greater than maximum {self.max}")
        return value


@dataclass(frozen=True)
class Int(_Numerical[int]):
    """`DataType` mapping to builtin ``int``."""

    @property
    def dtype(self) -> type[int]:
        return int


@dataclass(frozen=True)
class Float(_Numerical[float]):
    """`DataType` mapping to builtin ``float``."""

    prec: int = 2

    @property
    def dtype(self) -> type[float]:
        return float


@dataclass(frozen=True)
class Bool(DataType[bool]):
    """`DataType` mapping to builtin ``bool``."""

    znam: str = "OFF"
    onam: str = "ON"

    @property
    def dtype(self) -> type[bool]:
        return bool


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    @property
    def dtype(self) -> type[str]:
        return str
