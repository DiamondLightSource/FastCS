from dataclasses import dataclass
from typing import TypeVar


@dataclass(kw_only=True)
class AttributeIORef:
    update_period: float | None = None


AttributeIORefT = TypeVar("AttributeIORefT", bound=AttributeIORef, covariant=True)
