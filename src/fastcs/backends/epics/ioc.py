from dataclasses import dataclass
from typing import Any, Callable, cast

from softioc import asyncio_dispatcher, builder, softioc

from fastcs.attributes import AttrMode, AttrR, AttrRW, AttrW
from fastcs.backend import Backend
from fastcs.cs_methods import MethodType
from fastcs.datatypes import Bool, DataType, Float, Int
from fastcs.mapping import Mapping


@dataclass
class EpicsIOCOptions:
    terminal: bool = True


def _get_input_record(pv_name: str, datatype: DataType) -> Any:
    if isinstance(datatype, Bool):
        return builder.boolIn(pv_name, ZNAM=datatype.znam, ONAM=datatype.onam)
    elif isinstance(datatype, Int):
        return builder.longIn(pv_name)
    elif isinstance(datatype, Float):
        return builder.aIn(pv_name, PREC=datatype.prec)


def _create_and_link_read_pv(pv_name: str, attribute: AttrR) -> None:
    record = _get_input_record(pv_name, attribute._datatype)

    async def async_wrapper(v):
        record.set(v)

    attribute.set_update_callback(async_wrapper)


def _get_output_record(pv_name: str, datatype: DataType, on_update: Callable) -> Any:
    if isinstance(datatype, Bool):
        return builder.boolOut(
            pv_name,
            ZNAM=datatype.znam,
            ONAM=datatype.onam,
            always_update=True,
            on_update=on_update,
        )
    elif isinstance(datatype, Int):
        return builder.longOut(pv_name, always_update=True, on_update=on_update)
    elif isinstance(datatype, Float):
        return builder.aOut(pv_name, always_update=True, on_update=on_update, PREC=2)


def _create_and_link_write_pv(pv_name: str, attribute: AttrW) -> None:
    record = _get_output_record(
        pv_name, attribute.datatype, on_update=attribute.process_without_display_update
    )

    async def async_wrapper(v):
        record.set(v)

    attribute.set_write_display_callback(async_wrapper)


def _create_and_link_command_pv(pv_name: str, method: Callable) -> None:
    async def wrapped_method(_: Any):
        await method()

    builder.aOut(pv_name, always_update=True, on_update=wrapped_method)


def _create_and_link_attribute_pvs(mapping: Mapping) -> None:
    for single_mapping in mapping.get_controller_mappings():
        path = single_mapping.controller.path
        for attr_name, attribute in single_mapping.attributes.items():
            attr_name = attr_name.title().replace("_", "")
            pv_name = path.upper() + ":" + attr_name if path else attr_name

            match attribute.mode:
                case AttrMode.READ:
                    attribute = cast(AttrR, attribute)
                    _create_and_link_read_pv(pv_name, attribute)
                case AttrMode.WRITE:
                    attribute = cast(AttrW, attribute)
                    _create_and_link_write_pv(pv_name, attribute)
                case AttrMode.READ_WRITE:
                    attribute = cast(AttrRW, attribute)
                    _create_and_link_read_pv(pv_name + "_RBV", attribute)
                    _create_and_link_write_pv(pv_name, attribute)


def _create_and_link_command_pvs(mapping: Mapping) -> None:
    for single_mapping in mapping.get_controller_mappings():
        path = single_mapping.controller.path
        for method_data in single_mapping.methods:
            if method_data.info.method_type == MethodType.command:
                name = method_data.name.title().replace("_", "")
                pv_name = path.upper() + ":" + name if path else name

                _create_and_link_command_pv(pv_name, method_data.method)


class EpicsIOC:
    def __init__(self, mapping: Mapping):
        self._mapping = mapping

    def run(self, options: EpicsIOCOptions | None = None) -> None:
        if options is None:
            options = EpicsIOCOptions()

        # Create an asyncio dispatcher; the event loop is now running
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        backend = Backend(self._mapping, dispatcher.loop)

        # Set the record prefix
        builder.SetDeviceName("MY-DEVICE-PREFIX")

        _create_and_link_attribute_pvs(self._mapping)

        _create_and_link_command_pvs(self._mapping)

        # Boilerplate to get the IOC started
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        backend.link_process_tasks()
        backend.run_initial_tasks()
        backend.start_scan_tasks()

        # Run the interactive shell
        global_variables = globals()
        global_variables.update(
            {
                "dispatcher": dispatcher,
                "mapping": self._mapping,
                "controller": self._mapping.controller,
            }
        )
        softioc.interactive_ioc(globals())
