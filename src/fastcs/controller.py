from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from copy import deepcopy
from typing import get_type_hints

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORefT
from fastcs.attributes import Attribute, AttrR, AttrW
from fastcs.datatypes import T
from fastcs.tracer import Tracer


class BaseController(Tracer):
    """Base class for controller."""

    #: Attributes passed from the device at runtime.
    attributes: dict[str, Attribute]

    description: str | None = None

    def __init__(
        self,
        path: list[str] | None = None,
        description: str | None = None,
        ios: Sequence[AttributeIO[T, AttributeIORefT]] | None = None,
    ) -> None:
        super().__init__()

        if (
            description is not None
        ):  # Use the argument over the one class defined description.
            self.description = description

        if not hasattr(self, "attributes"):
            self.attributes = {}
        self._path: list[str] = path or []
        self.__sub_controller_tree: dict[str, Controller] = {}

        self._bind_attrs()

        ios = ios or []
        self._attribute_ref_io_map = {io.ref_type: io for io in ios}
        self._validate_io(ios)

    async def initialise(self):
        """Hook to dynamically add attributes before building the API"""
        pass

    def connect_attribute_ios(self) -> None:
        """Connect ``Attribute`` callbacks to ``AttributeIO``s"""
        for attr in self.attributes.values():
            ref = attr.io_ref if attr.has_io_ref() else None
            if ref is None:
                continue

            io = self._attribute_ref_io_map.get(type(ref))
            if io is None:
                raise ValueError(
                    f"{self.__class__.__name__} does not have an AttributeIO "
                    f"to handle {attr.io_ref.__class__.__name__}"
                )

            if isinstance(attr, AttrW):
                attr.set_on_put_callback(io.send)
            if isinstance(attr, AttrR):
                attr.set_update_callback(io.update)

        for controller in self.sub_controllers.values():
            controller.connect_attribute_ios()

    @property
    def path(self) -> list[str]:
        """Path prefix of attributes, recursively including parent Controllers."""
        return self._path

    def set_path(self, path: list[str]):
        if self._path:
            raise ValueError(f"sub controller is already registered under {self.path}")

        self._path = path
        for attribute in self.attributes.values():
            attribute.set_path(path)

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
        from fastcs.cs_methods import UnboundCommand, UnboundScan

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
                setattr(self, attr_name, deepcopy(attr))
            elif isinstance(attr, UnboundScan | UnboundCommand):
                setattr(self, attr_name, attr.bind(self))

    def _validate_io(self, ios: Sequence[AttributeIO[T, AttributeIORefT]]):
        """Validate that there is exactly one AttributeIO class registered to the
        controller for each type of AttributeIORef belonging to the attributes of the
        controller"""
        for ref_type, count in Counter([io.ref_type for io in ios]).items():
            if count > 1:
                raise RuntimeError(
                    f"More than one AttributeIO class handles {ref_type.__name__}"
                )

    def add_attribute(self, name, attribute: Attribute):
        if name in self.attributes and attribute is not self.attributes[name]:
            raise ValueError(
                f"Cannot add attribute {attribute}. "
                f"Controller {self} has has existing attribute {name}: "
                f"{self.attributes[name]}"
            )
        elif name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Cannot add attribute {attribute}. "
                f"Controller {self} has existing sub controller {name}: "
                f"{self.__sub_controller_tree[name]}"
            )

        attribute.set_name(name)
        attribute.set_path(self.path)
        self.attributes[name] = attribute
        super().__setattr__(name, attribute)

    def add_sub_controller(self, name: str, sub_controller: Controller):
        if name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Cannot add sub controller {sub_controller}. "
                f"Controller {self} has existing sub controller {name}: "
                f"{self.__sub_controller_tree[name]}"
            )
        elif name in self.attributes:
            raise ValueError(
                f"Cannot add sub controller {sub_controller}. "
                f"Controller {self} has existing attribute {name}: "
                f"{self.attributes[name]}"
            )

        sub_controller.set_path(self.path + [name])
        self.__sub_controller_tree[name] = sub_controller
        super().__setattr__(name, sub_controller)

        if isinstance(sub_controller.root_attribute, Attribute):
            self.attributes[name] = sub_controller.root_attribute

    @property
    def sub_controllers(self) -> dict[str, Controller]:
        return self.__sub_controller_tree

    def __repr__(self):
        name = self.__class__.__name__
        path = ".".join(self.path) or None
        sub_controllers = list(self.sub_controllers.keys()) or None

        return f"{name}(path={path}, sub_controllers={sub_controllers})"

    def __setattr__(self, name, value):
        if isinstance(value, Attribute):
            self.add_attribute(name, value)
        elif isinstance(value, Controller):
            self.add_sub_controller(name, value)
        else:
            super().__setattr__(name, value)


class Controller(BaseController):
    """Top-level controller for a device.

    This is the primary class for implementing device support in FastCS. Instances of
    this class can be loaded into a FastCS to expose its ``Attribute``s to the transport
    layer, which can then perform a specific function with the set of ``Attributes``,
    such as generating a UI or creating parameters for a control system.
    """

    root_attribute: Attribute | None = None

    def __init__(
        self,
        description: str | None = None,
        ios: Sequence[AttributeIO[T, AttributeIORefT]] | None = None,
    ) -> None:
        super().__init__(description=description, ios=ios)

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass
