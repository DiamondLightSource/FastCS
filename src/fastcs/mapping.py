from dataclasses import dataclass
from typing import Callable, NamedTuple

from .attributes import Attribute
from .controller import BaseController, Controller
from .cs_methods import MethodInfo

MethodData = NamedTuple(
    "MethodData", (("name", str), ("info", MethodInfo), ("method", Callable))
)


@dataclass
class SingleMapping:
    controller: BaseController
    methods: list[MethodData]
    attributes: dict[str, Attribute]


class Mapping:
    def __init__(self, controller: Controller) -> None:
        self.controller = controller

        self._controller_mappings: list[SingleMapping] = []
        self._generate_mapping(controller)
        self._controller_mappings.append(self._get_single_mapping(controller))

        for sub_controller in controller.get_sub_controllers():
            self._controller_mappings.append(self._get_single_mapping(sub_controller))

    @staticmethod
    def _get_single_mapping(controller: BaseController) -> SingleMapping:
        methods = []
        attributes = {}
        for attr_name in dir(controller):
            attr = getattr(controller, attr_name)
            if hasattr(attr, "fastcs_method_info"):
                methods.append(MethodData(attr_name, attr.fastcs_method_info, attr))
            elif isinstance(attr, Attribute):
                attributes[attr_name] = attr

        return SingleMapping(controller, methods, attributes)

    def __str__(self) -> str:
        result = "Controller mappings:\n"
        for mapping in self._controller_mappings:
            result += f"{mapping}\n"
        return result

    def get_controller_mappings(self) -> list[SingleMapping]:
        return self._controller_mappings
