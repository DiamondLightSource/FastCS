from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

import numpy as np

T = TypeVar("T", int, float, bool, str, np.ndarray)  # type: ignore
ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


@dataclass(frozen=True)  # So that we can type hint with dataclass methods
class DataType(Generic[T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    @property
    @abstractmethod
    def dtype(
        self,
    ) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass

    @property
    @abstractmethod
    def initial_value(self) -> T:
        """Return an initial value for the datatype."""
        pass

    @abstractmethod
    def cast(self, value: Any) -> T:
        """Cast a value to the datatype to put to the backend."""
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

    @property
    def initial_value(self) -> Literal[0]:
        return 0

    def cast(self, value: Any) -> int:
        if self.min is not None and value < self.min:
            raise ValueError(f"Value {value} is less than minimum {self.min}")
        if self.max is not None and value > self.max:
            raise ValueError(f"Value {value} is greater than maximum {self.max}")
        return int(value)


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

    @property
    def intial_value(self) -> float:
        return 0.0

    def cast(self, value: Any) -> float:
        if self.min is not None and value < self.min:
            raise ValueError(f"Value {value} is less than minimum {self.min}")
        if self.max is not None and value > self.max:
            raise ValueError(f"Value {value} is greater than maximum {self.max}")
        return float(value)


@dataclass(frozen=True)
class Bool(DataType[bool]):
    """`DataType` mapping to builtin ``bool``."""

    znam: str = "OFF"
    onam: str = "ON"

    @property
    def dtype(self) -> type[bool]:
        return bool

    @property
    def intial_value(self) -> Literal[False]:
        return False

    def cast(self, value: Any) -> bool:
        return bool(value)


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    @property
    def dtype(self) -> type[str]:
        return str

    @property
    def intial_value(self) -> Literal[""]:
        return ""

    def cast(self, value: Any) -> str:
        return str(value)


DEFAULT_WAVEFORM_LENGTH = 20000


@dataclass(frozen=True)
class WaveForm(DataType[np.ndarray]):
    """
    DataType for a waveform, values are of the numpy `datatype`
    """

    numpy_datatype: np.dtype
    length: int = DEFAULT_WAVEFORM_LENGTH

    @property
    def dtype(self) -> type[np.ndarray]:
        return np.ndarray

    @property
    def initial_value(self) -> np.ndarray:
        return np.ndarray(self.length, dtype=self.numpy_datatype)

    def cast(self, value: Sequence | np.ndarray) -> np.ndarray:
        if len(value) > self.length:
            raise ValueError(
                f"Waveform length {len(value)} is greater than maximum {self.length}."
            )
        if isinstance(value, np.ndarray):
            if value.dtype != self.numpy_datatype:
                raise ValueError(
                    f"Waveform dtype {value.dtype} does not "
                    f"match {self.numpy_datatype}."
                )
            return value
        else:
            return np.array(value, dtype=self.numpy_datatype)
