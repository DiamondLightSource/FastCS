import asyncio
from types import MethodType

from p4p.server import Server, StaticProvider

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller

from .types import AccessModeType, PviTree, make_command_pv, make_shared_pv

_attr_to_access: dict[type[Attribute], AccessModeType] = {
    AttrR: "r",
    AttrW: "w",
    AttrRW: "rw",
}


def get_pv_name(pv_prefix: str, attribute_name: str) -> str:
    return f"{pv_prefix}:{attribute_name.title().replace('_', '')}"


async def parse_attributes(
    prefix_root: str, controller: Controller
) -> list[StaticProvider]:
    providers = []
    pvi_tree = PviTree()

    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path
        pv_prefix = ":".join([prefix_root] + path)
        provider = StaticProvider(pv_prefix)
        providers.append(provider)

        for attr_name, attribute in single_mapping.attributes.items():
            pv_name = get_pv_name(pv_prefix, attr_name)
            attribute_pv = make_shared_pv(attribute)
            provider.add(pv_name, attribute_pv)
            pvi_tree.add_field(pv_name, _attr_to_access[type(attribute)])

        for attr_name, method in single_mapping.command_methods.items():
            pv_name = get_pv_name(pv_prefix, attr_name)
            command_pv = make_command_pv(
                MethodType(method.fn, single_mapping.controller)
            )
            provider.add(pv_name, command_pv)
            pvi_tree.add_field(pv_name, "command")

        pvi_tree.add_block(pv_prefix, description=single_mapping.controller.description)

    providers.append(pvi_tree.make_provider())
    return providers


class P4PIOC:
    def __init__(
        self,
        pv_prefix: str,
        controller: Controller,
    ):
        self.pv_prefix = pv_prefix
        self.controller = controller

    async def run(self):
        providers = await parse_attributes(self.pv_prefix, self.controller)

        endless_event = asyncio.Event()
        with Server(providers):
            await endless_event.wait()
