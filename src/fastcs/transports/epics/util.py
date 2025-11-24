import re

from fastcs.transports.controller_api import ControllerAPI


def snake_to_pascal(name: str) -> str:
    """Converts string from snake case to Pascal case.
    If string is not a valid snake case it will be returned unchanged
    """
    if re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", name):
        name = re.sub(r"(?:^|_)([a-z0-9])", lambda match: match.group(1).upper(), name)
    return name


def controller_pv_prefix(prefix: str, controller_api: ControllerAPI) -> str:
    return ":".join([prefix] + [snake_to_pascal(node) for node in controller_api.path])
