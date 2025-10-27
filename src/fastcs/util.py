import re
from typing import _GenericAlias, get_args, get_origin, get_type_hints  # type: ignore

import numpy as np

from fastcs.attributes import Attribute
from fastcs.controller import BaseController
from fastcs.datatypes import Bool, DataType, Float, Int, String


def snake_to_pascal(name: str) -> str:
    """Converts string from snake case to Pascal case.
    If string is not a valid snake case it will be returned unchanged
    """
    if re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", name):
        name = re.sub(r"(?:^|_)([a-z0-9])", lambda match: match.group(1).upper(), name)
    return name


def numpy_to_fastcs_datatype(np_type) -> DataType:
    """Converts numpy types to fastcs types for widget creation.
    Only types important for widget creation are explicitly converted
    """
    if np.issubdtype(np_type, np.integer):
        return Int()
    elif np.issubdtype(np_type, np.floating):
        return Float()
    elif np.issubdtype(np_type, np.bool_):
        return Bool()
    else:
        return String()


def validate_hinted_attributes(controller: BaseController):
    """Validates that type-hinted attributes in the controller and all subcontrollers
    exist with the right datatype and access mode.
    """
    for subcontroller in controller.get_sub_controllers().values():
        validate_hinted_attributes(subcontroller)
    hints = {
        k: v
        for k, v in get_type_hints(type(controller)).items()
        if isinstance(v, _GenericAlias | type)
    }
    for name, hint in hints.items():
        if isinstance(hint, type):
            attr_class = hint
            attr_dtype = None
        else:
            attr_class = get_origin(hint)
            attr_dtype = get_args(hint)[0]
        if not issubclass(attr_class, Attribute):
            continue
        attr = getattr(controller, name, None)
        if attr is None:
            raise RuntimeError(
                f"Controller `{controller.__class__.__name__}` failed to introspect "
                f"hinted attribute `{name}` during initialisation"
            )
        if attr_class is not type(attr):
            # skip validation if access mode not specified
            if attr_class is Attribute and isinstance(attr, Attribute):
                continue
            raise RuntimeError(
                f"Controller '{controller.__class__.__name__}' introspection of hinted "
                f"attribute '{name}' does not match defined access mode. "
                f"Expected '{attr_class.__name__}', got '{type(attr).__name__}'."
            )
        if attr_dtype is not None and attr_dtype != attr.datatype.dtype:
            raise RuntimeError(
                f"Controller '{controller.__class__.__name__}' introspection of hinted "
                f"attribute '{name}' does not match defined datatype. "
                f"Expected '{attr_dtype.__name__}', "
                f"got '{attr.datatype.dtype.__name__}'."
            )
