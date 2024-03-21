from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T", int, float, bool, str)
ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


class DataType(Generic[T]):
    """Generic datatype mapping to a python type, with additional metadata."""

    @property
    @abstractmethod
    def dtype(self) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass


@dataclass(frozen=True)
class Int(DataType[int]):
    """`DataType` mapping to builtin ``int``."""

    @property
    def dtype(self) -> type[int]:
        return int


@dataclass(frozen=True)
class Float(DataType[float]):
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
