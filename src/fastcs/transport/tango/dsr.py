from collections.abc import Awaitable, Callable
from typing import Any

import tango
from tango import AttrWriteType, Database, DbDevInfo, DevState, server
from tango.server import Device

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController
from fastcs.datatypes import Float

from .options import TangoDSROptions


def _wrap_updater_fget(
    attr_name: str, attribute: AttrR, controller: BaseController
) -> Callable[[Any], Any]:
    async def fget(tango_device: Device):
        tango_device.info_stream(f"called fget method: {attr_name}")
        return attribute.get()

    return fget


def _tango_display_format(attribute: Attribute) -> str:
    match attribute.datatype:
        case Float(prec):
            return f"%.{prec}"

    return "6.2f"  # `tango.server.attribute` default for `format`


def _wrap_updater_fset(
    attr_name: str, attribute: AttrW, controller: BaseController
) -> Callable[[Any, Any], Any]:
    async def fset(tango_device: Device, val):
        tango_device.info_stream(f"called fset method: {attr_name}")
        await attribute.process(val)

    return fset


def _collect_dev_attributes(controller: BaseController) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path

        for attr_name, attribute in single_mapping.attributes.items():
            attr_name = attr_name.title().replace("_", "")
            d_attr_name = f"{'_'.join(path)}_{attr_name}" if path else attr_name

            match attribute:
                case AttrRW():
                    collection[d_attr_name] = server.attribute(
                        label=d_attr_name,
                        dtype=attribute.datatype.dtype,
                        fget=_wrap_updater_fget(
                            attr_name, attribute, single_mapping.controller
                        ),
                        fset=_wrap_updater_fset(
                            attr_name, attribute, single_mapping.controller
                        ),
                        access=AttrWriteType.READ_WRITE,
                        format=_tango_display_format(attribute),
                    )
                case AttrR():
                    collection[d_attr_name] = server.attribute(
                        label=d_attr_name,
                        dtype=attribute.datatype.dtype,
                        access=AttrWriteType.READ,
                        fget=_wrap_updater_fget(
                            attr_name, attribute, single_mapping.controller
                        ),
                        format=_tango_display_format(attribute),
                    )
                case AttrW():
                    collection[d_attr_name] = server.attribute(
                        label=d_attr_name,
                        dtype=attribute.datatype.dtype,
                        access=AttrWriteType.WRITE,
                        fset=_wrap_updater_fset(
                            attr_name, attribute, single_mapping.controller
                        ),
                        format=_tango_display_format(attribute),
                    )

    return collection


def _wrap_command_f(
    method_name: str, method: Callable, controller: BaseController
) -> Callable[..., Awaitable[None]]:
    async def _dynamic_f(tango_device: Device) -> None:
        tango_device.info_stream(
            f"called {'_'.join(controller.path)} f method: {method_name}"
        )
        return await getattr(controller, method.__name__)()

    _dynamic_f.__name__ = method_name
    return _dynamic_f


def _collect_dev_commands(controller: BaseController) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path

        for name, method in single_mapping.command_methods.items():
            cmd_name = name.title().replace("_", "")
            d_cmd_name = f"{'_'.join(path)}_{cmd_name}" if path else cmd_name
            collection[d_cmd_name] = server.command(
                f=_wrap_command_f(d_cmd_name, method.fn, single_mapping.controller)
            )

    return collection


def _collect_dev_properties(controller: BaseController) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    return collection


def _collect_dev_init(controller: BaseController) -> dict[str, Callable]:
    async def init_device(tango_device: Device):
        await server.Device.init_device(tango_device)  # type: ignore
        tango_device.set_state(DevState.ON)

    return {"init_device": init_device}


def _collect_dev_flags(controller: BaseController) -> dict[str, Any]:
    collection: dict[str, Any] = {}

    collection["green_mode"] = tango.GreenMode.Asyncio

    return collection


def _collect_dsr_args(options: TangoDSROptions) -> list[str]:
    args = []

    if options.debug:
        args.append("-v4")

    return args


class TangoDSR:
    def __init__(self, controller: BaseController):
        self._controller = controller
        self.dev_class = self._controller.__class__.__name__
        self._device = self._create_device()

    def _create_device(self):
        class_dict: dict = {
            **_collect_dev_attributes(self._controller),
            **_collect_dev_commands(self._controller),
            **_collect_dev_properties(self._controller),
            **_collect_dev_init(self._controller),
            **_collect_dev_flags(self._controller),
        }

        class_bases = (server.Device,)
        pytango_class = type(self.dev_class, class_bases, class_dict)
        return pytango_class

    def run(self, options: TangoDSROptions | None = None) -> None:
        if options is None:
            options = TangoDSROptions()

        dsr_args = _collect_dsr_args(options)

        server.run(
            (self._device,),
            [self.dev_class, options.dsr_instance, *dsr_args],
            green_mode=server.GreenMode.Asyncio,
        )


def register_dev(dev_name: str, dev_class: str, dsr_instance: str) -> None:
    dsr_name = f"{dev_class}/{dsr_instance}"
    dev_info = DbDevInfo()
    dev_info.name = dev_name
    dev_info._class = dev_class  # noqa
    dev_info.server = dsr_name

    db = Database()
    db.delete_device(dev_name)  # Remove existing device entry
    db.add_device(dev_info)

    # Validate registration by reading
    read_dev_info = db.get_device_info(dev_info.name)

    print("Registered on Tango Database:")
    print(f" - Device: {read_dev_info.name}")
    print(f" - Class: {read_dev_info.class_name}")
    print(f" - Device server: {read_dev_info.ds_full_name}")
