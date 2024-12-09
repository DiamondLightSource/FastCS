from __future__ import annotations

import enum
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import MISSING, dataclass, field
from functools import cached_property
from typing import Generic, TypeVar

T = TypeVar("T", int, float, bool, str, enum.Enum)

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
    def initial_value(self) -> T:
        return self.dtype()


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


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    allowed_values: list[str] | None = None

    @property
    def dtype(self) -> type[str]:
        return str


T_Enum = TypeVar("T_Enum", bound=enum.Enum)


@dataclass(frozen=True)
class Enum(DataType[enum.Enum]):
    enum_cls: type[enum.Enum]

    @cached_property
    def is_string_enum(self) -> bool:
        return all(isinstance(member.value, str) for member in self.members)

    @cached_property
    def is_int_enum(self) -> bool:
        return all(isinstance(member.value, int) for member in self.members)

    def __post_init__(self):
        if not issubclass(self.enum_cls, enum.Enum):
            raise ValueError("Enum class has to take an enum.")
        if not (self.is_string_enum or self.is_int_enum):
            raise ValueError("All enum values must be of type str or int.")

    @cached_property
    def members(self) -> list[enum.Enum]:
        return list(self.enum_cls)

    @property
    def dtype(self) -> type[enum.Enum]:
        return self.enum_cls

    @property
    def initial_value(self) -> enum.Enum:
        return self.members[0]
