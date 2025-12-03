from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from copy import deepcopy
from typing import (
    Annotated,
    _GenericAlias,  # type: ignore
    get_args,
    get_origin,
    get_type_hints,
)

from fastcs.attributes import (
    Attribute,
    AttributeInfo,
    AttributeIO,
    AttributeIORefT,
    AttrR,
    AttrW,
    HintedAttribute,
)
from fastcs.datatypes import DType_T
from fastcs.logging import bind_logger
from fastcs.tracer import Tracer

logger = bind_logger(logger_name=__name__)


class BaseController(Tracer):
    """Base class for controllers

    Instances of this class can be loaded into FastCS to expose its Attributes to
    the transport layer, which can then perform a specific function such as generating a
    UI or creating parameters for a control system.

    This class is public for type hinting purposes, but should not be inherited to
    implement device drivers. Use either ``Controller`` or ``ControllerVector`` instead.

    """

    # These class attributes can be overridden on child classes to define default
    # behaviour of instantiated controllers
    root_attribute: Attribute | None = None
    description: str | None = None

    def __init__(
        self,
        path: list[str] | None = None,
        description: str | None = None,
        ios: Sequence[AttributeIO[DType_T, AttributeIORefT]] | None = None,
    ) -> None:
        super().__init__()

        if description is not None:
            # Use the argument over the one class defined description.
            self.description = description

        self._path: list[str] = path or []

        # Internal state that should not be accessed directly by base classes
        self.__attributes: dict[str, Attribute] = {}
        self.__sub_controllers: dict[str, BaseController] = {}

        self.__hinted_attributes: dict[str, HintedAttribute] = {}
        self.__hinted_sub_controllers: dict[str, type[BaseController]] = {}
        self._find_type_hints()

        self._bind_attrs()

        ios = ios or []
        self._attribute_ref_io_map = {io.ref_type: io for io in ios}
        self._validate_io(ios)

    def _find_type_hints(self):
        """Find `Attribute` and `Controller` type hints for introspection validation"""
        for name, hint in get_type_hints(type(self), include_extras=True).items():
            # Annotated[AttrR[int], AttributeInfo(...)]
            metadata = None
            if isinstance(origin := get_origin(hint), type) and origin is Annotated:
                args = get_args(hint)
                hint, metadata = args[0], args[1:]

            if isinstance(hint, _GenericAlias):  # e.g. AttrR[int]
                args = get_args(hint)
                hint = get_origin(hint)
            else:
                args = None

            if isinstance(hint, type) and issubclass(hint, Attribute):
                if args is None:
                    dtype = None
                else:
                    if len(args) != 2:
                        raise TypeError(
                            f"Invalid type hint for attribute {name}: {hint}"
                        )

                    dtype, _io_ref = args
                    if metadata is not None:
                        if not isinstance(metadata[0], AttributeInfo):
                            raise TypeError(
                                f"Invalid annotation for attribute {name}: {hint}"
                            )
                        else:
                            info = metadata[0]
                    else:
                        info = None

                    self.__hinted_attributes[name] = HintedAttribute(
                        attr_type=origin, dtype=dtype, info=info
                    )

            elif isinstance(hint, type) and issubclass(hint, BaseController):
                self.__hinted_sub_controllers[name] = hint

    def _bind_attrs(self) -> None:
        """Search for Attributes and Methods to bind them to this instance.

        This method will search the attributes of this controller class to bind them to
        this specific instance. For Attributes, this is just a case of copying and
        re-assigning to ``self`` to make it unique across multiple instances of this
        controller class. For Methods, this requires creating a bound method from a
        class method and a controller instance, so that it can be called from any
        context with the controller instance passed as the ``self`` argument.

        """
        # Lazy import to avoid circular references
        from fastcs.methods.command import UnboundCommand
        from fastcs.methods.scan import UnboundScan

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

    def _validate_io(self, ios: Sequence[AttributeIO[DType_T, AttributeIORefT]]):
        """Validate that there is exactly one AttributeIO class registered to the
        controller for each type of AttributeIORef belonging to the attributes of the
        controller"""
        for ref_type, count in Counter([io.ref_type for io in ios]).items():
            if count > 1:
                raise RuntimeError(
                    f"More than one AttributeIO class handles {ref_type.__name__}"
                )

    def __repr__(self):
        name = self.__class__.__name__
        path = ".".join(self.path) or None
        sub_controllers = list(self.sub_controllers.keys()) or None

        return f"{name}(path={path}, sub_controllers={sub_controllers})"

    def __setattr__(self, name, value):
        if isinstance(value, Attribute):
            self.add_attribute(name, value)
        elif isinstance(value, BaseController):
            self.add_sub_controller(name, value)
        else:
            super().__setattr__(name, value)

    async def initialise(self):
        """Hook for subclasses to dynamically add attributes before building the API"""
        pass

    def post_initialise(self):
        """Hook to call after all attributes added, before serving the application"""
        self._validate_type_hints()
        self._connect_attribute_ios()

    def _validate_type_hints(self):
        """Validate all `Attribute` and `Controller` type-hints were introspected"""
        for name in self.__hinted_attributes:
            self._validate_hinted_attribute(name)

        for name in self.__hinted_sub_controllers:
            self._validate_hinted_controller(name)

        for subcontroller in self.sub_controllers.values():
            subcontroller._validate_type_hints()  # noqa: SLF001

    def _validate_hinted_attribute(self, name: str):
        """Check that an `Attribute` with the given name exists on the controller"""
        attr = getattr(self, name, None)
        if attr is None or not isinstance(attr, Attribute):
            raise RuntimeError(
                f"Controller `{self.__class__.__name__}` failed to introspect "
                f"hinted attribute `{name}` during initialisation"
            )
        else:
            logger.debug(
                "Validated hinted attribute",
                name=name,
                controller=self,
                attribute=attr,
            )

    def _validate_hinted_controller(self, name: str):
        """Check that a sub controller with the given name exists on the controller"""
        controller = getattr(self, name, None)
        if controller is None or not isinstance(controller, BaseController):
            raise RuntimeError(
                f"Controller `{self.__class__.__name__}` failed to introspect "
                f"hinted controller `{name}` during initialisation"
            )
        else:
            logger.debug(
                "Validated hinted sub controller",
                name=name,
                controller=self,
                sub_controller=controller,
            )

    def _connect_attribute_ios(self) -> None:
        """Connect ``Attribute`` callbacks to ``AttributeIO``s"""
        for attr in self.__attributes.values():
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
            controller._connect_attribute_ios()  # noqa: SLF001

    @property
    def path(self) -> list[str]:
        """Path prefix of attributes, recursively including parent Controllers."""
        return self._path

    def set_path(self, path: list[str]):
        if self._path:
            raise ValueError(f"sub controller is already registered under {self.path}")

        self._path = path
        for attribute in self.__attributes.values():
            attribute.set_path(path)

    def add_attribute(self, name, attr: Attribute):
        if name in self.__attributes:
            raise ValueError(
                f"Cannot add attribute {attr}. "
                f"Controller {self} has has existing attribute {name}: "
                f"{self.__attributes[name]}"
            )
        elif name in self.__hinted_attributes:
            hint = self.__hinted_attributes[name]
            if not isinstance(attr, hint.attr_type):
                raise RuntimeError(
                    f"Controller '{self.__class__.__name__}' introspection of "
                    f"hinted attribute '{name}' does not match defined access mode. "
                    f"Expected '{hint.attr_type.__name__}' got '{type(attr).__name__}'."
                )
            if hint.dtype is not None and hint.dtype != attr.datatype.dtype:
                raise RuntimeError(
                    f"Controller '{self.__class__.__name__}' introspection of "
                    f"hinted attribute '{name}' does not match defined datatype. "
                    f"Expected '{hint.dtype.__name__}', "
                    f"got '{attr.datatype.dtype.__name__}'."
                )

            if hint.info is not None:
                attr.add_info(hint.info)

        elif name in self.__sub_controllers.keys():
            raise ValueError(
                f"Cannot add attribute {attr}. "
                f"Controller {self} has existing sub controller {name}: "
                f"{self.__sub_controllers[name]}"
            )

        attr.set_name(name)
        attr.set_path(self.path)
        self.__attributes[name] = attr
        super().__setattr__(name, attr)

    @property
    def attributes(self) -> dict[str, Attribute]:
        return self.__attributes

    def add_sub_controller(self, name: str, sub_controller: BaseController):
        if name in self.__sub_controllers.keys():
            raise ValueError(
                f"Cannot add sub controller {sub_controller}. "
                f"Controller {self} has existing sub controller {name}: "
                f"{self.__sub_controllers[name]}"
            )
        elif name in self.__hinted_sub_controllers:
            hint = self.__hinted_sub_controllers[name]
            if not isinstance(sub_controller, hint):
                raise RuntimeError(
                    f"Controller '{self.__class__.__name__}' introspection of "
                    f"hinted sub controller '{name}' does not match defined type. "
                    f"Expected '{hint.__name__}' got "
                    f"'{sub_controller.__class__.__name__}'."
                )
        elif name in self.__attributes:
            raise ValueError(
                f"Cannot add sub controller {sub_controller}. "
                f"Controller {self} has existing attribute {name}: "
                f"{self.__attributes[name]}"
            )

        sub_controller.set_path(self.path + [name])
        self.__sub_controllers[name] = sub_controller
        super().__setattr__(name, sub_controller)

        if isinstance(sub_controller.root_attribute, Attribute):
            self.__attributes[name] = sub_controller.root_attribute

    @property
    def sub_controllers(self) -> dict[str, BaseController]:
        return self.__sub_controllers
