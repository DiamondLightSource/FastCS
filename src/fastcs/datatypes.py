from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T", int, float, bool)
ATTRIBUTE_TYPES: tuple[type] = T.__constraints__  # type: ignore


AttrCallback = Callable[[T], Awaitable[None]]


class DataType(Generic[T]):
    @property
    @abstractmethod
    def dtype(self) -> type[T]:  # Using property due to lack of Generic ClassVars
        pass


@dataclass(frozen=True)
class Int(DataType[int]):
    @property
    def dtype(self) -> type[int]:
        return int


@dataclass(frozen=True)
class Float(DataType[float]):
    prec: int = 2

    @property
    def dtype(self) -> type[float]:
        return float


@dataclass(frozen=True)
class Bool(DataType[bool]):
    znam: str = "OFF"
    onam: str = "ON"

    @property
    def dtype(self) -> type[bool]:
        return bool
