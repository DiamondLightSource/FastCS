from dataclasses import dataclass

from typing_extensions import TypeVar


@dataclass(kw_only=True)
class AttributeIORef:
    """Base for references to define IO for an ``Attribute`` over an API.

    This object acts as a specification of the API that its corresponding
    ``AttributeIO`` should access for a given ``Attribute``. The fields necessary to
    distinguish between different ``Attributes`` is an implementation detail of the IO,
    but some examples are a string to send over a TCP port, or URI within an HTTP
    server.
    """

    update_period: float | None = None


AttributeIORefT = TypeVar(
    "AttributeIORefT", bound=AttributeIORef, default=AttributeIORef
)
