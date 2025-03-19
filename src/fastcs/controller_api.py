from collections.abc import Iterator
from dataclasses import dataclass, field

from fastcs.attributes import Attribute
from fastcs.cs_methods import Command, Put, Scan


@dataclass
class ControllerAPI:
    """Attributes, bound methods and sub APIs of a `Controller` / `SubController`"""

    path: list[str] = field(default_factory=list)
    """Path within controller tree (empty if this is the root)"""
    attributes: dict[str, Attribute] = field(default_factory=dict)
    command_methods: dict[str, Command] = field(default_factory=dict)
    put_methods: dict[str, Put] = field(default_factory=dict)
    scan_methods: dict[str, Scan] = field(default_factory=dict)
    sub_apis: dict[str, "ControllerAPI"] = field(default_factory=dict)
    """APIs of the sub controllers of the `Controller` this API was built from"""
    description: str | None = None

    def walk_api(self) -> Iterator["ControllerAPI"]:
        """Walk through all the nested `ControllerAPI` s of this `ControllerAPI`.

        Yields the `ControllerAPI` s from a depth-first traversal of the tree,
        including self.

        """
        yield self
        for api in self.sub_apis.values():
            yield from api.walk_api()
