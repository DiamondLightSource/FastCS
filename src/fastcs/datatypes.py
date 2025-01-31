from __future__ import annotations

import enum
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Generic, TypeVar

import numpy as np
from numpy.typing import DTypeLike

T = TypeVar("T", int, float, bool, str, enum.Enum, np.ndarray)

ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


@dataclass(frozen=True)
class DataType(Generic[T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    @property
    @abstractmethod
    def dtype(self) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass

    def validate(self, value: T) -> T:
        """Validate a value against fields in the datatype."""
        if not isinstance(value, self.dtype):
            raise ValueError(f"Value {value} is not of type {self.dtype}")

        return value

    @property
    @abstractmethod
    def initial_value(self) -> T:
        pass


T_Numerical = TypeVar("T_Numerical", int, float)


@dataclass(frozen=True)
class _Numerical(DataType[T_Numerical]):
    units: str | None = None
    min: int | None = None
    max: int | None = None
    min_alarm: int | None = None
    max_alarm: int | None = None

    def validate(self, value: T_Numerical) -> T_Numerical:
        super().validate(value)
        if self.min is not None and value < self.min:
            raise ValueError(f"Value {value} is less than minimum {self.min}")
        if self.max is not None and value > self.max:
            raise ValueError(f"Value {value} is greater than maximum {self.max}")
        return value

    @property
    def initial_value(self) -> T_Numerical:
        return self.dtype(0)


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

    @property
    def dtype(self) -> type[bool]:
        return bool

    @property
    def initial_value(self) -> bool:
        return False


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    @property
    def dtype(self) -> type[str]:
        return str

    @property
    def initial_value(self) -> str:
        return ""


T_Enum = TypeVar("T_Enum", bound=enum.Enum)


@dataclass(frozen=True)
class Enum(Generic[T_Enum], DataType[T_Enum]):
    enum_cls: type[T_Enum]

    def __post_init__(self):
        if not issubclass(self.enum_cls, enum.Enum):
            raise ValueError("Enum class has to take an Enum.")

    def index_of(self, value: T_Enum) -> int:
        return self.members.index(value)

    @cached_property
    def members(self) -> list[T_Enum]:
        return list(self.enum_cls)

    @property
    def dtype(self) -> type[T_Enum]:
        return self.enum_cls

    @property
    def initial_value(self) -> T_Enum:
        return self.members[0]


@dataclass(frozen=True)
class Waveform(DataType[np.ndarray]):
    array_dtype: DTypeLike
    shape: tuple[int, ...] = (2000,)

    @property
    def dtype(self) -> type[np.ndarray]:
        return np.ndarray

    @property
    def initial_value(self) -> np.ndarray:
        return np.zeros(self.shape, dtype=self.array_dtype)

    def validate(self, value: np.ndarray) -> np.ndarray:
        super().validate(value)
        if self.array_dtype != value.dtype:
            raise ValueError(
                f"Value dtype {value.dtype} is not the same as the array dtype "
                f"{self.array_dtype}"
            )
        if len(self.shape) != len(value.shape) or any(
            shape1 > shape2
            for shape1, shape2 in zip(value.shape, self.shape, strict=True)
        ):
            raise ValueError(
                f"Value shape {value.shape} exceeeds the shape maximum shape "
                f"{self.shape}"
            )
        return value
