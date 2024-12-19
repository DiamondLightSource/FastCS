from __future__ import annotations

import enum
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Generic, TypeVar

import numpy as np

T = TypeVar("T", int, float, bool, str, enum.IntEnum, np.ndarray)

ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


@dataclass(frozen=True)
class DataType(Generic[T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    # We move this to each datatype so that we can have positional
    # args in subclasses.
    allowed_values: list[T] | None = field(init=False, default=None)

    @property
    @abstractmethod
    def dtype(self) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass

    def validate(self, value: T) -> T:
        """Validate a value against fields in the datatype."""
        if not isinstance(value, self.dtype):
            raise ValueError(f"Value {value} is not of type {self.dtype}")
        if (
            hasattr(self, "allowed_values")
            and self.allowed_values is not None
            and value not in self.allowed_values
        ):
            raise ValueError(
                f"Value {value} is not in the allowed values for this "
                f"datatype {self.allowed_values}."
            )
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

    allowed_values: list[int] | None = None

    @property
    def dtype(self) -> type[int]:
        return int


@dataclass(frozen=True)
class Float(_Numerical[float]):
    """`DataType` mapping to builtin ``float``."""

    prec: int = 2
    allowed_values: list[float] | None = None

    @property
    def dtype(self) -> type[float]:
        return float


@dataclass(frozen=True)
class Bool(DataType[bool]):
    """`DataType` mapping to builtin ``bool``."""

    znam: str = "OFF"
    onam: str = "ON"
    allowed_values: list[bool] | None = None

    @property
    def dtype(self) -> type[bool]:
        return bool

    @property
    def initial_value(self) -> bool:
        return False


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    allowed_values: list[str] | None = None

    @property
    def dtype(self) -> type[str]:
        return str

    @property
    def initial_value(self) -> str:
        return ""


T_Enum = TypeVar("T_Enum", bound=enum.IntEnum)


@dataclass(frozen=True)
class Enum(DataType[enum.IntEnum]):
    enum_cls: type[enum.IntEnum]

    @cached_property
    def is_string_enum(self) -> bool:
        return all(isinstance(member.value, str) for member in self.members)

    def __post_init__(self):
        if not issubclass(self.enum_cls, enum.IntEnum):
            raise ValueError("Enum class has to take an IntEnum.")
        if {member.value for member in self.members} != set(range(len(self.members))):
            raise ValueError("Enum values must be contiguous.")

    @cached_property
    def members(self) -> list[enum.IntEnum]:
        return list(self.enum_cls)

    @property
    def dtype(self) -> type[enum.IntEnum]:
        return self.enum_cls

    @property
    def initial_value(self) -> enum.IntEnum:
        return self.members[0]


@dataclass(frozen=True)
class WaveForm(DataType[np.ndarray]):
    array_dtype: np.typing.DTypeLike
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
