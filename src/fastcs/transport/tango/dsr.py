import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import tango
from tango import AttrWriteType, Database, DbDevInfo, DevState, server
from tango.server import Device

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.cs_methods import CommandCallback

from .options import TangoDSROptions
from .util import (
    cast_from_tango_type,
    cast_to_tango_type,
    get_server_metadata_from_attribute,
    get_server_metadata_from_datatype,
)


def _wrap_updater_fget(
    attr_name: str,
    attribute: AttrR,
    controller_api: ControllerAPI,
) -> Callable[[Any], Any]:
    async def fget(tango_device: Device):
        tango_device.info_stream(f"called fget method: {attr_name}")
        return cast_to_tango_type(attribute.datatype, attribute.get())

    return fget


async def _run_threadsafe_blocking(
    coro: Coroutine[Any, Any, Any], loop: asyncio.AbstractEventLoop
) -> None:
    """
    Wraps a concurrent.futures.Future object as an
    asyncio.Future to make it awaitable and then awaits it
    """
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    await asyncio.wrap_future(future)


def _wrap_updater_fset(
    attr_name: str,
    attribute: AttrW,
    controller_api: ControllerAPI,
    loop: asyncio.AbstractEventLoop,
) -> Callable[[Any, Any], Any]:
    async def fset(tango_device: Device, value):
        tango_device.info_stream(f"called fset method: {attr_name}")
        coro = attribute.process(cast_from_tango_type(attribute.datatype, value))
        await _run_threadsafe_blocking(coro, loop)

    return fset


def _collect_dev_attributes(
    root_controller_api: ControllerAPI, loop: asyncio.AbstractEventLoop
) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    for controller_api in root_controller_api.walk_api():
        path = controller_api.path

        for attr_name, attribute in controller_api.attributes.items():
            attr_name = attr_name.title().replace("_", "")
            d_attr_name = f"{'_'.join(path)}_{attr_name}" if path else attr_name

            match attribute:
                case AttrRW():
                    collection[d_attr_name] = server.attribute(
                        label=d_attr_name,
                        fget=_wrap_updater_fget(attr_name, attribute, controller_api),
                        fset=_wrap_updater_fset(
                            attr_name, attribute, controller_api, loop
                        ),
                        access=AttrWriteType.READ_WRITE,
                        **get_server_metadata_from_attribute(attribute),
                        **get_server_metadata_from_datatype(attribute.datatype),
                    )
                case AttrR():
                    collection[d_attr_name] = server.attribute(
                        label=d_attr_name,
                        access=AttrWriteType.READ,
                        fget=_wrap_updater_fget(attr_name, attribute, controller_api),
                        **get_server_metadata_from_attribute(attribute),
                        **get_server_metadata_from_datatype(attribute.datatype),
                    )
                case AttrW():
                    collection[d_attr_name] = server.attribute(
                        label=d_attr_name,
                        access=AttrWriteType.WRITE,
                        fset=_wrap_updater_fset(
                            attr_name, attribute, controller_api, loop
                        ),
                        **get_server_metadata_from_attribute(attribute),
                        **get_server_metadata_from_datatype(attribute.datatype),
                    )

    return collection


def _wrap_command_f(
    method_name: str,
    method: CommandCallback,
    controller_api: ControllerAPI,
    loop: asyncio.AbstractEventLoop,
) -> Callable[..., Awaitable[None]]:
    async def _dynamic_f(tango_device: Device) -> None:
        tango_device.info_stream(
            f"called {'_'.join(controller_api.path)} f method: {method_name}"
        )

        coro = method()
        await _run_threadsafe_blocking(coro, loop)

    _dynamic_f.__name__ = method_name
    return _dynamic_f


def _collect_dev_commands(
    root_controller_api: ControllerAPI,
    loop: asyncio.AbstractEventLoop,
) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    for controller_api in root_controller_api.walk_api():
        path = controller_api.path

        for name, method in controller_api.command_methods.items():
            cmd_name = name.title().replace("_", "")
            d_cmd_name = f"{'_'.join(path)}_{cmd_name}" if path else cmd_name
            collection[d_cmd_name] = server.command(
                f=_wrap_command_f(d_cmd_name, method.fn, controller_api, loop)
            )

    return collection


def _collect_dev_properties(controller_api: ControllerAPI) -> dict[str, Any]:
    collection: dict[str, Any] = {}
    return collection


def _collect_dev_init(controller_api: ControllerAPI) -> dict[str, Callable]:
    async def init_device(tango_device: Device):
        await server.Device.init_device(tango_device)  # type: ignore
        tango_device.set_state(DevState.ON)

    return {"init_device": init_device}


def _collect_dev_flags(controller_api: ControllerAPI) -> dict[str, Any]:
    collection: dict[str, Any] = {}

    collection["green_mode"] = tango.GreenMode.Asyncio

    return collection


def _collect_dsr_args(options: TangoDSROptions) -> list[str]:
    args = []

    if options.debug:
        args.append("-v4")

    return args


class TangoDSR:
    """For controlling a controller with tango.

    Avoid running directly, instead use `fastcs.launch.FastCS`.
    """

    def __init__(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ):
        self._controller_api = controller_api
        self._loop = loop
        self.dev_class = self._controller_api.__class__.__name__
        self._device = self._create_device()

    def _create_device(self):
        class_dict: dict = {
            **_collect_dev_attributes(self._controller_api, self._loop),
            **_collect_dev_commands(self._controller_api, self._loop),
            **_collect_dev_properties(self._controller_api),
            **_collect_dev_init(self._controller_api),
            **_collect_dev_flags(self._controller_api),
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
    """Register a device instance in the tango server."""
    dsr_name = f"{dev_class}/{dsr_instance}"
    dev_info = DbDevInfo(dev_name, dev_class, dsr_name)

    db = Database()
    db.delete_device(dev_name)  # Remove existing device entry
    db.add_device(dev_info)

    # Validate registration by reading
    read_dev_info = db.get_device_info(dev_info.name)

    print("Registered on Tango Database:")
    print(f" - Device: {read_dev_info.name}")
    print(f" - Class: {read_dev_info.class_name}")
    print(f" - Device server: {read_dev_info.ds_full_name}")
