import asyncio
import re
from types import MethodType

from p4p.server import Server, StaticProvider

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller

from ._pv_handlers import make_command_pv, make_shared_pv
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


def _snake_to_pascal(name: str) -> str:
    name = re.sub(
        r"(?:^|_)([a-z])", lambda match: match.group(1).upper(), name
    ).replace("_", "")
    return re.sub(r"_(\d+)$", r"\1", name)


def get_pv_name(pv_prefix: str, *attribute_names: str) -> str:
    pv_formatted = ":".join([_snake_to_pascal(attr) for attr in attribute_names])
    return f"{pv_prefix}:{pv_formatted}" if pv_formatted else pv_prefix


async def parse_attributes(
    root_pv_prefix: str, controller: Controller
) -> list[StaticProvider]:
    pvi_tree = PviTree(root_pv_prefix)
    provider = StaticProvider(root_pv_prefix)

    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path
        pv_prefix = get_pv_name(root_pv_prefix, *path)

        pvi_tree.add_sub_device(
            pv_prefix,
            single_mapping.controller.description,
        )

        for attr_name, attribute in single_mapping.attributes.items():
            pv_name = get_pv_name(pv_prefix, attr_name)
            attribute_pv = make_shared_pv(attribute)
            provider.add(pv_name, attribute_pv)
            pvi_tree.add_signal(pv_name, _attribute_to_access(attribute))

        for attr_name, method in single_mapping.command_methods.items():
            pv_name = get_pv_name(pv_prefix, attr_name)
            command_pv = make_command_pv(
                MethodType(method.fn, single_mapping.controller)
            )
            provider.add(pv_name, command_pv)
            pvi_tree.add_signal(pv_name, "x")

    return [provider, pvi_tree.make_provider()]


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
