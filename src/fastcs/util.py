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
        attr = getattr(controller, name, None)
        assert attr is not None, (
            f"Controller `{controller.__class__.__name__}` failed to introspect hinted "
            f"attribute `{name}` during initialisation"
        )
        assert type(attr) is attr_class, (
            f"Controller '{controller.__class__.__name__}' introspection of hinted "
            f"attribute '{name}' does not match defined access mode. "
            f"Expected '{attr_class.__name__}', got '{type(attr).__name__}'."
        )
        # TypeError raised if the number of args if not 1
        (attr_dtype,) = get_args(hint)
        assert attr.datatype.dtype == attr_dtype, (
            f"Controller '{controller.__class__.__name__}' introspection of hinted "
            f"attribute '{name}' does not match defined datatype. "
            f"Expected '{attr_dtype.__name__}', got '{attr.datatype.dtype.__name__}'."
        )
