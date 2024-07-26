from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import MethodType
from typing import Any

import tango
from tango import AttrWriteType, Database, DbDevInfo, DevState, server
from tango.server import Device

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.backend import (
    _link_attribute_sender_class,
    _link_single_controller_put_tasks,
)
from fastcs.controller import BaseController
from fastcs.datatypes import Float
from fastcs.mapping import Mapping


@dataclass
class TangoDSROptions:
    dev_name: str = "MY/DEVICE/NAME"
    dev_class: str = "FAST_CS_DEVICE"
    dsr_instance: str = "MY_SERVER_INSTANCE"
    debug: bool = False


def _wrap_updater_fget(
    attr_name: str, attribute: AttrR, controller: BaseController
) -> Callable[[Any], Any]:
    async def fget(tango_device: Device):
        assert attribute.updater is not None

        await attribute.updater.update(controller, attribute)
        tango_device.info_stream(f"called fget method: {attr_name}")
        return attribute.get()

    return fget


def _tango_polling_period(attribute: AttrR) -> int:
    if attribute.updater is not None:
        # Convert to integer milliseconds
        return int(attribute.updater.update_period * 1000)

    return -1  # `tango.server.attribute` default for `polling_period`


def _tango_display_format(attribute: Attribute) -> str:
    match attribute.datatype:
        case Float(prec):
            return f"%.{prec}"

    return "6.2f"  # `tango.server.attribute` default for `format`


def _wrap_updater_fset(
    attr_name: str, attribute: AttrW, controller: BaseController
) -> Callable[[Any, Any], Any]:
    async def fset(tango_device: Device, val):
        assert attribute.sender is not None

        await attribute.sender.put(controller, attribute, val)
        tango_device.info_stream(f"called fset method: {attr_name}")

    return fset


def _collect_dev_attributes(mapping: Mapping) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    for single_mapping in mapping.get_controller_mappings():
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
                        polling_period=_tango_polling_period(attribute),
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
                        polling_period=_tango_polling_period(attribute),
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
        tango_device.info_stream(f"called {controller} f method: {method_name}")
        return await MethodType(method, controller)()

    _dynamic_f.__name__ = method_name
    return _dynamic_f


def _collect_dev_commands(mapping: Mapping) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    for single_mapping in mapping.get_controller_mappings():
        path = single_mapping.controller.path

        for name, method in single_mapping.command_methods.items():
            cmd_name = name.title().replace("_", "")
            d_cmd_name = f"{'_'.join(path)}_{cmd_name}" if path else cmd_name
            collection[d_cmd_name] = server.command(
                f=_wrap_command_f(d_cmd_name, method.fn, single_mapping.controller)
            )

    return collection


def _collect_dev_properties(mapping: Mapping) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    return collection


def _collect_dev_init(mapping: Mapping) -> dict[str, Callable]:
    async def init_device(tango_device: Device):
        await server.Device.init_device(tango_device)
        tango_device.set_state(DevState.ON)
        await mapping.controller.connect()

    return {"init_device": init_device}


def _collect_dev_flags(mapping: Mapping) -> dict[str, Any]:
    collection: dict[str, Any] = {}

    collection["green_mode"] = tango.GreenMode.Asyncio

    return collection


def _collect_dsr_args(options: TangoDSROptions) -> list[str]:
    args = []

    if options.debug:
        args.append("-v4")

    return args


class TangoDSR:
    def __init__(self, mapping: Mapping):
        self._mapping = mapping

    def _link_process_tasks(self) -> None:
        for single_mapping in self._mapping.get_controller_mappings():
            _link_single_controller_put_tasks(single_mapping)
            _link_attribute_sender_class(single_mapping)

    def run(self, options: TangoDSROptions | None = None) -> None:
        if options is None:
            options = TangoDSROptions()

        self._link_process_tasks()

        class_dict: dict = {
            **_collect_dev_attributes(self._mapping),
            **_collect_dev_commands(self._mapping),
            **_collect_dev_properties(self._mapping),
            **_collect_dev_init(self._mapping),
            **_collect_dev_flags(self._mapping),
        }

        class_bases = (server.Device,)
        pytango_class = type(options.dev_class, class_bases, class_dict)
        register_dev(options.dev_name, options.dev_class, options.dsr_instance)

        dsr_args = _collect_dsr_args(options)

        server.run(
            (pytango_class,),
            [options.dev_class, options.dsr_instance, *dsr_args],
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
