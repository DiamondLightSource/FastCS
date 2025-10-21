from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from copy import deepcopy
from typing import get_type_hints

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORefT
from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
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
        pass

    async def attribute_initialise(self) -> None:
        """Register update and send callbacks for attributes on this controller
        and all subcontrollers"""
        self._add_io_callbacks()

        for controller in self.get_sub_controllers().values():
            await controller.attribute_initialise()

    def _add_io_callbacks(self):
        for attr in self.attributes.values():
            ref = attr.io_ref if attr.has_io_ref() else None
            io = self._attribute_ref_io_map.get(type(ref))
            if isinstance(attr, AttrW):
                attr.add_process_callback(self._create_send_callback(io, attr, ref))
            if isinstance(attr, AttrR):
                attr.add_update_callback(self._create_update_callback(io, attr, ref))

    def _create_send_callback(self, io, attr, ref):
        if ref is None:

            async def send_callback(value):
                await attr.update_display_without_process(value)
                if isinstance(attr, AttrRW):
                    await attr.set(value)
        else:

            async def send_callback(value):
                await io.send(attr, value)

        return send_callback

    def _create_update_callback(self, io, attr, ref):
        if ref is None:

            async def error_callback():
                raise RuntimeError("Can't call update on Attributes without an io_ref")

            return error_callback
        else:

            async def update_callback():
                await io.update(attr)

            return update_callback

    @property
    def path(self) -> list[str]:
        """Path prefix of attributes, recursively including parent Controllers."""
        return self._path

    def set_path(self, path: list[str]):
        if self._path:
            raise ValueError(f"sub controller is already registered under {self.path}")

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
                setattr(self, attr_name, deepcopy(attr))
            elif isinstance(attr, UnboundPut | UnboundScan | UnboundCommand):
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

        for attr in self.attributes.values():
            if not attr.has_io_ref():
                continue
            assert type(attr.io_ref) in self._attribute_ref_io_map, (
                f"{self.__class__.__name__} does not have an AttributeIO to handle "
                f"{attr.io_ref.__class__.__name__}"
            )

    def add_attribute(self, name, attribute: Attribute):
        if name in self.attributes and attribute is not self.attributes[name]:
            raise ValueError(
                f"Cannot add attribute {name}. "
                f"Controller {self} has has existing attribute {name}"
            )
        elif name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Cannot add attribute {name}. "
                f"Controller {self} has existing sub controller {name}"
            )

        attribute.set_name(name)
        self.attributes[name] = attribute
        super().__setattr__(name, attribute)

    def register_sub_controller(self, name: str, sub_controller: Controller):
        if name in self.__sub_controller_tree.keys():
            raise ValueError(
                f"Controller {self} already has a sub controller registered as {name}"
            )

        self.__sub_controller_tree[name] = sub_controller
        sub_controller.set_path(self.path + [name])

        if isinstance(sub_controller.root_attribute, Attribute):
            if name in self.attributes:
                raise TypeError(
                    f"Cannot set sub controller `{name}` root attribute "
                    f"on the parent controller `{type(self).__name__}` "
                    f"as it already has an attribute of that name."
                )
            self.attributes[name] = sub_controller.root_attribute

    def get_sub_controllers(self) -> dict[str, Controller]:
        return self.__sub_controller_tree

    def __repr__(self):
        return f"""\
{type(self).__name__}({self.path}, {list(self.__sub_controller_tree.keys())})\
"""

    def __setattr__(self, name, value):
        if isinstance(value, Attribute):
            self.add_attribute(name, value)
        else:
            super().__setattr__(name, value)


class Controller(BaseController):
    """Top-level controller for a device.

    This is the primary class for implementing device support in FastCS. Instances of
    this class can be loaded into a backend to access its ``Attribute``s. The backend
    can then perform a specific function with the set of ``Attributes``, such as
    generating a UI or creating parameters for a control system.
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
