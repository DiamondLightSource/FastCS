import asyncio

from p4p.server import Server, StaticProvider

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.transport.epics.util import controller_pv_prefix
from fastcs.util import snake_to_pascal

from ._pv_handlers import (
    make_command_pv,
    make_shared_read_pv,
    make_shared_write_pv,
)
from .pvi import add_pvi_info


async def parse_attributes(
    root_pv_prefix: str, root_controller_api: ControllerAPI
) -> StaticProvider:
    """Parses `Attribute` s into p4p signals in handlers."""
    provider = StaticProvider(root_pv_prefix)

    for controller_api in root_controller_api.walk_api():
        pv_prefix = controller_pv_prefix(root_pv_prefix, controller_api)
        add_pvi_info(
            provider=provider,
            pv_prefix=pv_prefix,
            controller_api=controller_api,
            description=controller_api.description,
        )

        for attr_name, attribute in controller_api.attributes.items():
            full_pv_name = f"{pv_prefix}:{snake_to_pascal(attr_name)}"
            match attribute:
                case AttrRW():
                    attribute_pv = make_shared_write_pv(attribute)
                    attribute_pv_rbv = make_shared_read_pv(attribute)
                    provider.add(f"{full_pv_name}", attribute_pv)
                    provider.add(f"{full_pv_name}_RBV", attribute_pv_rbv)
                case AttrR():
                    attribute_pv = make_shared_read_pv(attribute)
                    provider.add(f"{full_pv_name}", attribute_pv)
                case AttrW():
                    attribute_pv = make_shared_write_pv(attribute)
                    provider.add(f"{full_pv_name}", attribute_pv)

        for attr_name, method in controller_api.command_methods.items():
            full_pv_name = f"{pv_prefix}:{snake_to_pascal(attr_name)}"
            command_pv = make_command_pv(method.fn)
            provider.add(f"{full_pv_name}", command_pv)

    return provider


class P4PIOC:
    """A P4P IOC which handles a controller"""

    def __init__(self, pv_prefix: str, controller_api: ControllerAPI):
        self.pv_prefix = pv_prefix
        self.controller_api = controller_api

    async def run(self):
        provider = await parse_attributes(self.pv_prefix, self.controller_api)

        endless_event = asyncio.Event()
        with Server([provider]):
            await endless_event.wait()
