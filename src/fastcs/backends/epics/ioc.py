from collections.abc import Callable
from dataclasses import dataclass
from types import MethodType
from typing import Any

from softioc import asyncio_dispatcher, builder, softioc
from softioc.pythonSoftIoc import RecordWrapper

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.backend import Backend
from fastcs.backends.epics.utils import get_epics_record_fields, get_mbb_record_fields
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.exceptions import FastCSException
from fastcs.mapping import Mapping


@dataclass
class EpicsIOCOptions:
    terminal: bool = True


def _get_input_record(pv_name: str, attribute: AttrR) -> RecordWrapper:
    datatype = attribute.datatype
    epics_kwargs = {
        k: v for k, v in attribute.kwargs.items() if k in get_epics_record_fields()
    }
    match datatype:
        case Bool(znam, onam):
            return builder.boolIn(pv_name, ZNAM=znam, ONAM=onam, **epics_kwargs)
        case Int():
            # check if we need to use an mbb record
            if any(True for kw in attribute.kwargs if kw in get_mbb_record_fields()):
                return builder.mbbIn(pv_name, **epics_kwargs)
            return builder.longIn(pv_name, **epics_kwargs)
        case Float(prec):
            return builder.aIn(pv_name, PREC=prec, **epics_kwargs)
        case String():
            return builder.longStringIn(pv_name, **epics_kwargs)
        case _:
            raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")


def _create_and_link_read_pv(pv_name: str, attribute: AttrR) -> None:
    record = _get_input_record(pv_name, attribute)

    async def async_wrapper(v):
        record.set(v)

    attribute.set_update_callback(async_wrapper)


def _get_output_record(pv_name: str, attribute: AttrW, on_update: Callable) -> Any:
    datatype = attribute.datatype
    epics_kwargs = {
        k: v for k, v in attribute.kwargs.items() if k in get_epics_record_fields()
    }
    match datatype:
        case Bool(znam, onam):
            return builder.boolOut(
                pv_name,
                ZNAM=znam,
                ONAM=onam,
                always_update=True,
                on_update=on_update,
                **epics_kwargs,
            )
        case Int():
            # check if we need to use an mbb record
            if any(True for kw in attribute.kwargs if kw in get_mbb_record_fields()):
                return builder.mbbOut(
                    pv_name, always_update=True, on_update=on_update, **epics_kwargs
                )
            return builder.longIn(pv_name, **epics_kwargs)
            if attribute.dropdown_mapping is None:
                return builder.longOut(pv_name, always_update=True, on_update=on_update)
        case Float(prec):
            return builder.aOut(
                pv_name,
                always_update=True,
                on_update=on_update,
                PREC=prec,
                **epics_kwargs,
            )
        case String():
            return builder.longStringOut(
                pv_name, always_update=True, on_update=on_update, **epics_kwargs
            )
        case _:
            raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")


def _create_and_link_write_pv(pv_name: str, attribute: AttrW) -> None:
    record = _get_output_record(
        pv_name, attribute, on_update=attribute.process_without_display_update
    )

    async def async_wrapper(v):
        record.set(v, process=False)

    attribute.set_write_display_callback(async_wrapper)


def _create_and_link_command_pv(pv_name: str, method: Callable) -> None:
    async def wrapped_method(_: Any):
        await method()

    builder.aOut(pv_name, initial_value=0, always_update=True, on_update=wrapped_method)


def _create_and_link_attribute_pvs(mapping: Mapping) -> None:
    for single_mapping in mapping.get_controller_mappings():
        path = single_mapping.controller.path
        for attr_name, attribute in single_mapping.attributes.items():
            attr_name = attr_name.title().replace("_", "")
            pv_name = f"{':'.join(path)}:{attr_name}" if path else attr_name

            match attribute:
                case AttrRW():
                    _create_and_link_read_pv(pv_name + "_RBV", attribute)
                    _create_and_link_write_pv(pv_name, attribute)
                case AttrR():
                    _create_and_link_read_pv(pv_name, attribute)
                case AttrW():
                    _create_and_link_write_pv(pv_name, attribute)


def _create_and_link_command_pvs(mapping: Mapping) -> None:
    for single_mapping in mapping.get_controller_mappings():
        path = single_mapping.controller.path
        for attr_name, method in single_mapping.command_methods.items():
            attr_name = attr_name.title().replace("_", "")
            pv_name = f"{':'.join(path)}:{attr_name}" if path else attr_name

            _create_and_link_command_pv(
                pv_name, MethodType(method.fn, single_mapping.controller)
            )


class EpicsIOC:
    def __init__(self, mapping: Mapping, pv_prefix: str):
        self._mapping = mapping
        self._pv_prefix = pv_prefix

    def run(self, options: EpicsIOCOptions | None = None) -> None:
        if options is None:
            options = EpicsIOCOptions()

        # Create an asyncio dispatcher; the event loop is now running
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        backend = Backend(self._mapping, dispatcher.loop)

        # Set the record prefix
        builder.SetDeviceName(self._pv_prefix)

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
