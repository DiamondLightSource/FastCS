from dataclasses import dataclass
from typing import Any

from fastcs.datatypes.datatype import DataType


@dataclass(frozen=True)
class String(DataType[str]):
    """`DataType` mapping to builtin ``str``."""

    length: int | None = None
    """Maximum length of string to display in transports. Must be >=1 or None."""

    def __post_init__(self):
        if self.length is not None and self.length < 1:
            raise ValueError("String length must be >= 1")

    @property
    def dtype(self) -> type[str]:
        return str

    @property
    def initial_value(self) -> str:
        return ""

    def validate(self, value: Any) -> str:
        """Truncate string to maximum length

        Returns:
            The string, truncated to the maximum length if set

        """
        return super().validate(value)[: self.length]
