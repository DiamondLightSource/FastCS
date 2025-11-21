from dataclasses import dataclass

from fastcs.datatypes.datatype import DataType


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    length: int | None = None
    """Maximum length of string to display in transports"""

    @property
    def dtype(self) -> type[str]:
        return str

    @property
    def initial_value(self) -> str:
        return ""
