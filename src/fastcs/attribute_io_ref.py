from dataclasses import dataclass

from typing_extensions import TypeVar


@dataclass(kw_only=True)
class AttributeIORef:
    update_period: float | None = None


AttributeIORefT = TypeVar(
    "AttributeIORefT", default=AttributeIORef, bound=AttributeIORef, covariant=True
)
