from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping, MutableMapping
from copy import deepcopy
from typing import get_type_hints

from fastcs.attributes import Attribute


class BaseController:
    """Base class for controller."""

    #: Attributes passed from the device at runtime.
    attributes: dict[str, Attribute]

    description: str | None = None

    def __init__(
        self, path: list[str | int] | None = None, description: str | None = None
    ) -> None:
        if (
            description is not None
        ):  # Use the argument over the one class defined description.
            self.description = description

        if not hasattr(self, "attributes"):
            self.attributes = {}
        self._path: list[str | int] = path or []
        self.__sub_controller_tree: dict[str | int, SubController] = {}

        self._bind_attrs()

    async def initialise(self):
        pass

    async def attribute_initialise(self) -> None:
        # Initialise any registered handlers for attributes
        coros = [attr.initialise(self) for attr in self.attributes.values()]
        try:
            await asyncio.gather(*coros)
        except asyncio.CancelledError:
            pass

        for controller in self.get_sub_controllers().values():
            await controller.attribute_initialise()

    @property
    def path(self) -> list[str | int]:
        """Path prefix of attributes, recursively including parent Controllers."""
        return self._path

    def set_path(self, path: list[str | int]):
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
        context with the controller instance passed as the `self` argument.

        """
        # Lazy import to avoid circular references
        from fastcs.cs_methods import UnboundCommand, UnboundPut, UnboundScan

        # Using a dictionary instead of a set to maintain order.
        class_dir = {key: None for key in dir(type(self)) if not key.startswith("_")}
        class_type_hints = {
            key: value
            for key, value in get_type_hints(type(self)).items()
            if not key.startswith("_")
        }

        for attr_name in {**class_dir, **class_type_hints}:
            if attr_name == "root_attribute":
                continue

            attr = getattr(self, attr_name, None)
            if isinstance(attr, Attribute):
                if (
                    attr_name in self.attributes
                    and self.attributes[attr_name] is not attr
                ):
                    raise ValueError(
                        f"`{type(self).__name__}` has conflicting attribute "
                        f"`{attr_name}` already present in the attributes dict."
                    )

                new_attribute = deepcopy(attr)
                setattr(self, attr_name, new_attribute)
                self.attributes[attr_name] = new_attribute
            elif isinstance(attr, UnboundPut | UnboundScan | UnboundCommand):
                setattr(self, attr_name, attr.bind(self))

    def register_sub_controller(self, name: str | int, sub_controller: SubController):
        if name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Controller {self} already has a SubController registered as {name}"
            )

        self.__sub_controller_tree[name] = sub_controller
        sub_controller.set_path(self.path + [name])

        if isinstance(sub_controller.root_attribute, Attribute):
            if name in self.attributes:
                raise TypeError(
                    f"Cannot set SubController `{name}` root attribute "
                    f"on the parent controller `{type(self).__name__}` "
                    f"as it already has an attribute of that name."
                )
            self.attributes[str(name)] = sub_controller.root_attribute

    def get_sub_controllers(self) -> dict[str | int, SubController]:
        return self.__sub_controller_tree


class Controller(BaseController):
    """Top-level controller for a device.

    This is the primary class for implementing device support in FastCS. Instances of
    this class can be loaded into a backend to access its ``Attribute``s. The backend
    can then perform a specific function with the set of ``Attributes``, such as
    generating a UI or creating parameters for a control system.
    """

    def __init__(self, description: str | None = None) -> None:
        super().__init__(description=description)

    async def connect(self) -> None:
        pass


class SubController(BaseController):
    """A subordinate to a ``Controller`` for managing a subset of a device.

    An instance of this class can be registered with a parent ``Controller`` to include
    it as part of a larger device.
    """

    root_attribute: Attribute | None = None

    def __init__(self, description: str | None = None) -> None:
        super().__init__(description=description)


class SubControllerVector(MutableMapping[int, SubController], SubController):
    """A collection of SubControllers, with an arbitrary integer index.
    An instance of this class can be registered with a parent ``Controller`` to include
    it's children as part of a larger controller. Each child of the vector will keep
    a string name of the vector.
    """

    def __init__(
        self, children: Mapping[int, SubController], description: str | None = None
    ) -> None:
        self._children: dict[int, SubController] = {}
        self.update(children)
        super().__init__(description=description)
        for index, child in children.items():
            self.register_sub_controller(index, child)

    def __getitem__(self, key: int) -> SubController:
        return self._children[key]

    def __setitem__(self, key: int, value: SubController) -> None:
        if not isinstance(key, int):
            msg = f"Expected int, got {key}"
            raise TypeError(msg)
        if not isinstance(value, SubController):
            msg = f"Expected SubController, got {value}"
            raise TypeError(msg)
        self._children[key] = value

    def __delitem__(self, key: int) -> None:
        del self._children[key]

    def __iter__(self) -> Iterator[int]:
        yield from self._children

    def __len__(self) -> int:
        return len(self._children)

    def children(self) -> Iterator[tuple[str, SubController]]:
        for key, child in self._children.items():
            yield str(key), child

    def __hash__(self):
        return hash(id(self))
