from __future__ import annotations

from copy import copy

from .attributes import Attribute


class BaseController:
    def __init__(self, path: list[str] | None = None) -> None:
        self._path: list[str] = path or []
        self.__sub_controller_tree: dict[str, SubController] = {}

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
        """Search for `Attributes` and `Methods` to bind them to this instance.

        This method will search the attributes of this controller class to bind them to
        this specific instance. For `Attribute`s, this is just a case of copying and
        re-assigning to `self` to make it unique across multiple instances of this
        controller class. For `Method`s, this requires creating a bound method from a
        class method and a controller instance, so that it can be called from any
        context with an implicit `self` argument as the instance.

        """
        # Lazy import to avoid circular references
        from fastcs.cs_methods import Command, Put, Scan

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, Attribute):
                setattr(self, attr_name, copy(attr))  # type: ignore
            elif isinstance(attr, Put | Scan | Command):
                setattr(self, attr_name, attr.bind(self))

    def register_sub_controller(self, name: str, sub_controller: SubController):
        if name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Controller {self} already has a SubController registered as {name}"
            )

        self.__sub_controller_tree[name] = sub_controller
        sub_controller.set_path(self.path + [name])

    def get_sub_controllers(self) -> dict[str, SubController]:
        return self.__sub_controller_tree


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
