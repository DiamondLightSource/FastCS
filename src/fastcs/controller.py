from __future__ import annotations

from copy import copy

from .attributes import Attribute


class BaseController:
    def __init__(self, path: list[str] | None = None) -> None:
        self._path: list[str] = path or []
        self.__sub_controllers: list[SubController] = []

        self._bind_attrs()

    @property
    def path(self) -> list[str]:
        """Path prefix of attributes, recursively including parent ``Controller``s."""
        return self._path

    def _bind_attrs(self) -> None:
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, Attribute):
                new_attribute = copy(attr)
                setattr(self, attr_name, new_attribute)

    def register_sub_controller(self, controller: SubController):
        self.__sub_controllers.append(controller)

    def get_sub_controllers(self) -> list[SubController]:
        return self.__sub_controllers


class Controller(BaseController):
    """Top-level controller for a device.

    This is the primary class for implementing device support in FastCS. Instances of
    this class can be loaded into a backend to access its ``Attribute``s. The backend
    can then perform a specific function with the set of ``Attributes``, such as
    generating a UI or creating parameters for a control system.
    """

    def __init__(self) -> None:
        super().__init__()

    async def connect(self) -> None:
        pass


class SubController(BaseController):
    """A subordinate to a ``Controller`` for managing a subset of a device.

    An instance of this class can be registered with a parent ``Controller`` to include
    it as part of a larger device.
    """

    def __init__(self, path: list[str]) -> None:
        super().__init__(path)
