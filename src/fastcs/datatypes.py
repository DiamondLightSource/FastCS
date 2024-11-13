from __future__ import annotations

import numpy as np
from numpy import typing as npt
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T", int, float, bool, str, npt.ArrayLike)
ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


@dataclass(frozen=True)  # So that we can type hint with dataclass methods
class DataType(Generic[T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    @property
    @abstractmethod
    def dtype(self) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass


@dataclass(frozen=True)
class Int(DataType[int]):
    """`DataType` mapping to builtin ``int``."""

    units: str | None = None
    min: int | None = None
    max: int | None = None
    min_alarm: int | None = None
    max_alarm: int | None = None

    @property
    def dtype(self) -> type[int]:
        return int


@dataclass(frozen=True)
class Float(DataType[float]):
    """`DataType` mapping to builtin ``float``."""

    prec: int = 2
    units: str | None = None
    min: float | None = None
    max: float | None = None
    min_alarm: float | None = None
    max_alarm: float | None = None

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


@dataclass(frozen=True)
class WaveForm(DataType[npt.ArrayLike]):
    """DataType for a waveform"""

    length: int | None = None

    @property
    def dtype(self) -> type[npt.ArrayLike]:
        return np.ndarray


@dataclass(frozen=True)
class Table(DataType[npt.ArrayLike]):
    """`DataType` mapping to a dictionary of numpy arrays.

    Values should be a dictionary of column name to an `ArrayLike` of columns.
    """

    numpy_datatype: npt.DTypeLike

    @property
    def dtype(self) -> type[npt.ArrayLike]:
        return np.ndarray


def validate_value(datatype: DataType[T], value: T) -> T:
    """Validate a value against a datatype."""

    if isinstance(datatype, (Int | Float)):
        assert isinstance(value, (int | float)), f"Value {value} is not a number"
        if datatype.min is not None and value < datatype.min:
            raise ValueError(f"Value {value} is less than minimum {datatype.min}")
        if datatype.max is not None and value > datatype.max:
            raise ValueError(f"Value {value} is greater than maximum {datatype.max}")
    return value
