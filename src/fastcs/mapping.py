from collections.abc import Iterator
from dataclasses import dataclass

from .attributes import Attribute
from .controller import BaseController, Controller
from .cs_methods import Command, Put, Scan
from .wrappers import WrappedMethod


@dataclass
class SingleMapping:
    controller: BaseController
    scan_methods: dict[str, Scan]
    put_methods: dict[str, Put]
    command_methods: dict[str, Command]
    attributes: dict[str, Attribute]


class Mapping:
    def __init__(self, controller: Controller) -> None:
        self.controller = controller
        self._controller_mappings = list(_walk_mappings(controller))

    def __str__(self) -> str:
        result = "Controller mappings:\n"
        for mapping in self._controller_mappings:
            result += f"{mapping}\n"
        return result

    def get_controller_mappings(self) -> list[SingleMapping]:
        return self._controller_mappings


def _walk_mappings(controller: BaseController) -> Iterator[SingleMapping]:
    yield _get_single_mapping(controller)
    for sub_controller in controller.get_sub_controllers().values():
        yield from _walk_mappings(sub_controller)


def _get_single_mapping(controller: BaseController) -> SingleMapping:
    scan_methods = {}
    put_methods = {}
    command_methods = {}
    attributes = {}
    for attr_name in dir(controller):
        attr = getattr(controller, attr_name)
        match attr:
            case WrappedMethod(fastcs_method=fastcs_method):
                match fastcs_method:
                    case Put():
                        put_methods[attr_name] = fastcs_method
                    case Scan():
                        scan_methods[attr_name] = fastcs_method
                    case Command():
                        command_methods[attr_name] = fastcs_method
            case Attribute():
                attributes[attr_name] = attr

    return SingleMapping(
        controller, scan_methods, put_methods, command_methods, attributes
    )
