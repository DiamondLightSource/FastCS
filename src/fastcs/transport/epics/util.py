from fastcs.controller_api import ControllerAPI
from fastcs.util import snake_to_pascal


def controller_pv_prefix(prefix: str, controller_api: ControllerAPI) -> str:
    return ":".join([prefix] + [snake_to_pascal(node) for node in controller_api.path])
