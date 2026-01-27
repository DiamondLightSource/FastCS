from collections.abc import Iterator
from dataclasses import dataclass, field

from fastcs.attributes import Attribute
from fastcs.logging import bind_logger
from fastcs.methods import Command, Scan
from fastcs.tracer import Tracer

tracer = Tracer(name=__name__)
logger = bind_logger(logger_name=__name__)


@dataclass
class ControllerAPI:
    """Attributes, Methods and sub APIs of a `Controller` to expose in a transport"""

    path: list[str] = field(default_factory=list)
    """Path within controller tree (empty if this is the root)"""
    attributes: dict[str, Attribute] = field(default_factory=dict)
    command_methods: dict[str, Command] = field(default_factory=dict)
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

    def __repr__(self):
        return (
            f"ControllerAPI("
            f"path={self.path}, "
            f"sub_apis=[{', '.join(self.sub_apis.keys())}]"
            f")"
        )
