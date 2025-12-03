from dataclasses import dataclass


@dataclass(kw_only=True)
class AttributeInfo:
    """Fields to apply to hinted attributes during introspection"""

    description: str | None = None
    group: str | None = None
