from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .attributes import Attribute
from .controller import BaseController, Controller
from .cs_methods import BoundCommand, BoundPut, BoundScan, Command, Put, Scan


@dataclass
class SingleMapping:
    controller: BaseController
    scan_methods: dict[str, BoundScan]
    put_methods: dict[str, BoundPut]
    command_methods: dict[str, BoundCommand]
    attributes: dict[str, Attribute[Any]]


class Mapping:
    def __init__(self, controller: Controller) -> None:
        self.controller = controller
        self._controller_mappings = tuple(_walk_mappings(controller))

    def __str__(self) -> str:
        result = "Controller mappings:\n"
        for mapping in self._controller_mappings:
            result += f"{mapping}\n"
        return result

    def get_controller_mappings(self) -> tuple[SingleMapping, ...]:
        return self._controller_mappings


def _walk_mappings(
    controller: BaseController,
) -> Iterator[SingleMapping]:
    yield get_single_mapping(controller)
    for sub_controller in controller.get_sub_controllers().values():
        yield from _walk_mappings(sub_controller)


def get_single_mapping(controller: BaseController) -> SingleMapping:
    scan_methods: dict[str, BoundScan] = {}
    put_methods: dict[str, BoundPut] = {}
    command_methods: dict[str, BoundCommand] = {}
    attributes: dict[str, Attribute[Any]] = {}
    for attr_name in dir(controller):
        attr = getattr(controller, attr_name)
        match attr:
            case Attribute(enabled=True):
                attributes[attr_name] = attr
            case BoundPut(enabled=True):
                put_methods[attr_name] = attr
            case Put(enabled=True):
                put_methods[attr_name] = attr.bind(controller)
            case BoundScan(enabled=True):
                scan_methods[attr_name] = attr
            case Scan(enabled=True):
                scan_methods[attr_name] = attr.bind(controller)
            case BoundCommand(enabled=True):
                command_methods[attr_name] = attr
            case Command(enabled=True):
                command_methods[attr_name] = attr.bind(controller)
            case _:
                pass

    return SingleMapping(
        controller, scan_methods, put_methods, command_methods, attributes
    )
