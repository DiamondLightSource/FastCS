import asyncio

from p4p.server import Server, StaticProvider

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.util import snake_to_pascal

from ._pv_handlers import (
    make_command_pv,
    make_shared_read_pv,
    make_shared_write_pv,
)
from .pvi_tree import AccessModeType, PviTree


def _attribute_to_access(attribute: Attribute) -> AccessModeType:
    match attribute:
        case AttrRW():
            return "rw"
        case AttrR():
            return "r"
        case AttrW():
            return "w"
        case _:
            raise ValueError(f"Unknown attribute type {type(attribute)}")


def get_pv_name(pv_prefix: str, *attribute_names: str) -> str:
    """Converts from an attribute name to a pv name."""
    pv_formatted = ":".join([snake_to_pascal(attr) for attr in attribute_names])
    return f"{pv_prefix}:{pv_formatted}" if pv_formatted else pv_prefix


async def parse_attributes(
    root_pv_prefix: str, root_controller_api: ControllerAPI
) -> list[StaticProvider]:
    """Parses `Attribute` s into p4p signals in handlers."""
    pvi_tree = PviTree(root_pv_prefix)
    provider = StaticProvider(root_pv_prefix)

    for controller_api in root_controller_api.walk_api():
        pv_prefix = get_pv_name(root_pv_prefix, *controller_api.path)

        pvi_tree.add_sub_device(pv_prefix, controller_api.description)

        for attr_name, attribute in controller_api.attributes.items():
            pv_name = get_pv_name(pv_prefix, attr_name)
            match attribute:
                case AttrRW():
                    attribute_pv = make_shared_write_pv(attribute)
                    attribute_pv_rbv = make_shared_read_pv(attribute)
                    provider.add(pv_name, attribute_pv)
                    provider.add(f"{pv_name}_RBV", attribute_pv_rbv)
                    pvi_tree.add_signal(pv_name, "rw")
                case AttrR():
                    attribute_pv = make_shared_read_pv(attribute)
                    provider.add(pv_name, attribute_pv)
                    pvi_tree.add_signal(pv_name, "r")
                case AttrW():
                    attribute_pv = make_shared_write_pv(attribute)
                    provider.add(pv_name, attribute_pv)
                    pvi_tree.add_signal(pv_name, "w")

        for attr_name, method in controller_api.command_methods.items():
            pv_name = get_pv_name(pv_prefix, attr_name)
            command_pv = make_command_pv(method.fn)
            provider.add(pv_name, command_pv)
            pvi_tree.add_signal(pv_name, "x")

    return [provider, pvi_tree.make_provider()]


class P4PIOC:
    """A P4P IOC which handles a controller.

    Avoid running directly, instead use `fastcs.launch.FastCS`.
    """

    def __init__(self, pv_prefix: str, controller_api: ControllerAPI):
        self.pv_prefix = pv_prefix
        self.controller_api = controller_api

    async def run(self):
        providers = await parse_attributes(self.pv_prefix, self.controller_api)

        endless_event = asyncio.Event()
        with Server(providers):
            await endless_event.wait()
