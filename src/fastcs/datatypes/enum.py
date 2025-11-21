import enum
from dataclasses import dataclass
from functools import cached_property
from typing import Generic, TypeVar

from fastcs.datatypes.datatype import DataType

Enum_T = TypeVar("Enum_T", bound=enum.Enum)
"""A builtin Enum type"""


@dataclass(frozen=True)
class Enum(Generic[Enum_T], DataType[Enum_T]):
    enum_cls: type[Enum_T]

    def __post_init__(self):
        if not issubclass(self.enum_cls, enum.Enum):
            raise ValueError("Enum class has to take an Enum.")

    def index_of(self, value: Enum_T) -> int:
        return self.members.index(value)

    @cached_property
    def members(self) -> list[Enum_T]:
        return list(self.enum_cls)

    @cached_property
    def names(self) -> list[str]:
        return [member.name for member in self.members]

    @property
    def dtype(self) -> type[Enum_T]:
        return self.enum_cls

    @property
    def initial_value(self) -> Enum_T:
        return self.members[0]
