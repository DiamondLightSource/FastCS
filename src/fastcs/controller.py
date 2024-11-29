from __future__ import annotations

from collections.abc import Iterator
from copy import copy
from dataclasses import dataclass

from .attributes import Attribute
from .cs_methods import Command, Put, Scan
from .wrappers import WrappedMethod


@dataclass
class SingleMapping:
    controller: BaseController
    scan_methods: dict[str, Scan]
    put_methods: dict[str, Put]
    command_methods: dict[str, Command]
    attributes: dict[str, Attribute]


class BaseController:
    def __init__(self, path: list[str] | None = None) -> None:
        self._path: list[str] = path or []
        self.__sub_controller_tree: dict[str, BaseController] = {}

        self._bind_attrs()

    @property
    def path(self) -> list[str]:
        """Path prefix of attributes, recursively including parent ``Controller``s."""
        return self._path

    def set_path(self, path: list[str]):
        if self._path:
            raise ValueError(f"SubController is already registered under {self.path}")

        self._path = path

    def _bind_attrs(self) -> None:
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, Attribute):
                new_attribute = copy(attr)
                setattr(self, attr_name, new_attribute)

    def register_sub_controller(self, name: str, sub_controller: SubController):
        if name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Controller {self} already has a SubController registered as {name}"
            )

        self.__sub_controller_tree[name] = sub_controller
        sub_controller.set_path(self.path + [name])

    def get_sub_controllers(self) -> dict[str, BaseController]:
        return self.__sub_controller_tree

    def get_controller_mappings(self) -> list[SingleMapping]:
        return list(_walk_mappings(self))


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


class Controller(BaseController):
    """Top-level controller for a device.

    This is the primary class for implementing device support in FastCS. Instances of
    this class can be loaded into a backend to access its ``Attribute``s. The backend
    can then perform a specific function with the set of ``Attributes``, such as
    generating a UI or creating parameters for a control system.
    """

    def __init__(self) -> None:
        super().__init__()

    async def initialise(self) -> None:
        pass

    async def connect(self) -> None:
        pass


class SubController(BaseController):
    """A subordinate to a ``Controller`` for managing a subset of a device.

    An instance of this class can be registered with a parent ``Controller`` to include
    it as part of a larger device.
    """

    def __init__(self) -> None:
        super().__init__()
