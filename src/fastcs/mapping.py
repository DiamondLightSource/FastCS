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
    scan_methods: dict[str, Scan] = {}
    put_methods: dict[str, Put] = {}
    command_methods: dict[str, Command] = {}
    attributes: dict[str, Attribute] = {}
    for attr_name in dir(controller):
        attr = getattr(controller, attr_name)
        match attr:
            case WrappedMethod(fastcs_method=Put(enabled=True) as put_method):
                put_methods[attr_name] = put_method
            case WrappedMethod(fastcs_method=Scan(enabled=True) as scan_method):
                scan_methods[attr_name] = scan_method
            case WrappedMethod(fastcs_method=Command(enabled=True) as command_method):
                command_methods[attr_name] = command_method
            case Attribute(enabled=True):
                attributes[attr_name] = attr

    return SingleMapping(
        controller, scan_methods, put_methods, command_methods, attributes
    )
