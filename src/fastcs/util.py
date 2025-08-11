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
    """Validates that type-hinted attributes exist in the controller, and are accessible
    via the dot accessor, from the attributes dictionary and with the right datatype.
    """
    hints = get_type_hints(type(controller))
    alias_hints = {k: v for k, v in hints.items() if isinstance(v, _GenericAlias)}
    for name, hint in alias_hints.items():
        attr_class = get_origin(hint)
        if not issubclass(attr_class, Attribute):
            continue
        args = get_args(hint)
        assert len(args) == 1, f"Hinted attribute {name} has too many arguments"
        (attr_dtype,) = args
        attr = getattr(controller, name, None)
        assert attr is not None, (
            f"No attribute named {name} bound on controller {controller}"
        )
        assert type(attr) is attr_class, (
            f"Expected {attr_class} for {name}, got {type(attr)}"
        )
        dict_attr = controller.attributes.get(name, None)
        assert dict_attr is not None, (
            f"Hinted attribute {name} not found in controller's attribute dict"
        )
        assert dict_attr is attr, (
            f"Hinted attribute {name} in controller's attribute dict"
            " is not the bound attribute"
        )
        assert attr.datatype.dtype == attr_dtype, (
            f"Expected dtype {attr_dtype} for {name}, got {attr.datatype.dtype}"
        )
