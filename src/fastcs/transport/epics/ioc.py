from collections.abc import Callable
from dataclasses import asdict
from types import MethodType
from typing import Any, Literal

from softioc import builder, softioc
from softioc.asyncio_dispatcher import AsyncioDispatcher
from softioc.pythonSoftIoc import RecordWrapper

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Bool, DataType, Float, Int, String, T
from fastcs.exceptions import FastCSException
from fastcs.transport.epics.util import (
    MBB_STATE_FIELDS,
    attr_is_enum,
    enum_index_to_value,
    enum_value_to_index,
)

from .options import EpicsIOCOptions

EPICS_MAX_NAME_LENGTH = 60


DATATYPE_NAME_TO_RECORD_FIELD = {
    "prec": "PREC",
    "units": "EGU",
    "min": "DRVL",
    "max": "DRVH",
    "min_alarm": "LOPR",
    "max_alarm": "HOPR",
    "znam": "ZNAM",
    "onam": "ONAM",
}


def datatype_to_epics_fields(datatype: DataType) -> dict[str, Any]:
    return {
        DATATYPE_NAME_TO_RECORD_FIELD[field]: value
        for field, value in asdict(datatype).items()
        if field in DATATYPE_NAME_TO_RECORD_FIELD
    }


class EpicsIOC:
    def __init__(
        self,
        pv_prefix: str,
        controller: Controller,
        options: EpicsIOCOptions | None = None,
    ):
        self.options = options or EpicsIOCOptions()
        self._controller = controller
        _add_pvi_info(f"{pv_prefix}:PVI")
        _add_sub_controller_pvi_info(pv_prefix, controller)

        _create_and_link_attribute_pvs(pv_prefix, controller)
        _create_and_link_command_pvs(pv_prefix, controller)

    def run(
        self,
        dispatcher: AsyncioDispatcher,
    ) -> None:
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        if self.options.terminal:
            context = {
                "dispatcher": dispatcher,
                "controller": self._controller,
            }
            softioc.interactive_ioc(context)


def _add_pvi_info(
    pvi: str,
    parent_pvi: str = "",
    name: str = "",
):
    """Add PVI metadata for a controller.

    Args:
        pvi: PVI PV of controller
        parent_pvi: PVI PV of parent controller
        name: Name to register controller with parent as

    """
    # Create a record to attach the info tags to
    record = builder.longStringIn(
        f"{pvi}_PV",
        initial_value=pvi,
        DESC="The records in this controller",
    )

    # Create PVI PV in preparation for adding attribute info tags to it
    q_group = {
        pvi: {
            "+id": "epics:nt/NTPVI:1.0",
            "display.description": {"+type": "plain", "+channel": "DESC"},
            "": {"+type": "meta", "+channel": "VAL"},
        }
    }
    # If this controller has a parent, add a link in the parent to this controller
    if parent_pvi and name:
        q_group.update(
            {
                parent_pvi: {
                    f"value.{name}.d": {
                        "+channel": "VAL",
                        "+type": "plain",
                        "+trigger": f"value.{name}.d",
                    }
                }
            }
        )

    record.add_info("Q:group", q_group)


def _add_sub_controller_pvi_info(pv_prefix: str, parent: BaseController):
    """Add PVI references from controller to its sub controllers, recursively.

    Args:
        pv_prefix: PV Prefix of IOC
        parent: Controller to add PVI refs for

    """
    parent_pvi = ":".join([pv_prefix] + parent.path + ["PVI"])

    for child in parent.get_sub_controllers().values():
        child_pvi = ":".join([pv_prefix] + child.path + ["PVI"])
        child_name = child.path[-1].lower()

        _add_pvi_info(child_pvi, parent_pvi, child_name)

        _add_sub_controller_pvi_info(pv_prefix, child)


def _create_and_link_attribute_pvs(pv_prefix: str, controller: Controller) -> None:
    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path
        for attr_name, attribute in single_mapping.attributes.items():
            pv_name = attr_name.title().replace("_", "")
            _pv_prefix = ":".join([pv_prefix] + path)
            full_pv_name_length = len(f"{_pv_prefix}:{pv_name}")

            if full_pv_name_length > EPICS_MAX_NAME_LENGTH:
                attribute.enabled = False
                print(
                    f"Not creating PV for {attr_name} for controller"
                    f" {single_mapping.controller.path} as full name would exceed"
                    f" {EPICS_MAX_NAME_LENGTH} characters"
                )
                continue

            match attribute:
                case AttrRW():
                    if full_pv_name_length > (EPICS_MAX_NAME_LENGTH - 4):
                        print(
                            f"Not creating PVs for {attr_name} as _RBV PV"
                            f" name would exceed {EPICS_MAX_NAME_LENGTH}"
                            " characters"
                        )
                        attribute.enabled = False
                    else:
                        _create_and_link_read_pv(
                            _pv_prefix, f"{pv_name}_RBV", attr_name, attribute
                        )
                        _create_and_link_write_pv(
                            _pv_prefix, pv_name, attr_name, attribute
                        )
                case AttrR():
                    _create_and_link_read_pv(_pv_prefix, pv_name, attr_name, attribute)
                case AttrW():
                    _create_and_link_write_pv(_pv_prefix, pv_name, attr_name, attribute)


def _create_and_link_read_pv(
    pv_prefix: str, pv_name: str, attr_name: str, attribute: AttrR[T]
) -> None:
    if attr_is_enum(attribute):

        async def async_record_set(value: T):
            record.set(enum_value_to_index(attribute, value))
    else:

        async def async_record_set(value: T):
            record.set(value)

    record = _get_input_record(f"{pv_prefix}:{pv_name}", attribute)
    _add_attr_pvi_info(record, pv_prefix, attr_name, "r")

    attribute.set_update_callback(async_record_set)


def _get_input_record(pv: str, attribute: AttrR) -> RecordWrapper:
    attribute_fields = {}
    if attribute.description is not None:
        attribute_fields.update({"DESC": attribute.description})

    if attr_is_enum(attribute):
        assert attribute.allowed_values is not None and all(
            isinstance(v, str) for v in attribute.allowed_values
        )
        state_keys = dict(zip(MBB_STATE_FIELDS, attribute.allowed_values, strict=False))
        return builder.mbbIn(pv, **state_keys, **attribute_fields)

    match attribute.datatype:
        case Bool():
            record = builder.boolIn(
                pv, **datatype_to_epics_fields(attribute.datatype), **attribute_fields
            )
        case Int():
            record = builder.longIn(
                pv,
                **datatype_to_epics_fields(attribute.datatype),
                **attribute_fields,
            )
        case Float():
            record = builder.aIn(
                pv,
                **datatype_to_epics_fields(attribute.datatype),
                **attribute_fields,
            )
        case String():
            record = builder.longStringIn(
                pv, **datatype_to_epics_fields(attribute.datatype), **attribute_fields
            )
        case _:
            raise FastCSException(
                f"Unsupported type {type(attribute.datatype)}: {attribute.datatype}"
            )

    def datatype_updater(datatype: DataType):
        for name, value in datatype_to_epics_fields(datatype).items():
            record.set_field(name, value)

    attribute.add_update_datatype_callback(datatype_updater)
    return record


def _create_and_link_write_pv(
    pv_prefix: str, pv_name: str, attr_name: str, attribute: AttrW[T]
) -> None:
    if attr_is_enum(attribute):

        async def on_update(value):
            await attribute.process_without_display_update(
                enum_index_to_value(attribute, value)
            )

        async def async_write_display(value: T):
            record.set(enum_value_to_index(attribute, value), process=False)

    else:

        async def on_update(value):
            await attribute.process_without_display_update(value)

        async def async_write_display(value: T):
            record.set(value, process=False)

    record = _get_output_record(
        f"{pv_prefix}:{pv_name}", attribute, on_update=on_update
    )

    _add_attr_pvi_info(record, pv_prefix, attr_name, "w")

    attribute.set_write_display_callback(async_write_display)


def _get_output_record(pv: str, attribute: AttrW, on_update: Callable) -> Any:
    attribute_fields = {}
    if attribute.description is not None:
        attribute_fields.update({"DESC": attribute.description})
    if attr_is_enum(attribute):
        assert attribute.allowed_values is not None and all(
            isinstance(v, str) for v in attribute.allowed_values
        )
        state_keys = dict(zip(MBB_STATE_FIELDS, attribute.allowed_values, strict=False))
        return builder.mbbOut(
            pv,
            always_update=True,
            on_update=on_update,
            **state_keys,
            **attribute_fields,
        )

    match attribute.datatype:
        case Bool():
            record = builder.boolOut(
                pv,
                **datatype_to_epics_fields(attribute.datatype),
                always_update=True,
                on_update=on_update,
            )
        case Int():
            record = builder.longOut(
                pv,
                always_update=True,
                on_update=on_update,
                **datatype_to_epics_fields(attribute.datatype),
                **attribute_fields,
            )
        case Float():
            record = builder.aOut(
                pv,
                always_update=True,
                on_update=on_update,
                **datatype_to_epics_fields(attribute.datatype),
                **attribute_fields,
            )
        case String():
            record = builder.longStringOut(
                pv, always_update=True, on_update=on_update, **attribute_fields
            )
        case _:
            raise FastCSException(
                f"Unsupported type {type(attribute.datatype)}: {attribute.datatype}"
            )

    def datatype_updater(datatype: DataType):
        for name, value in datatype_to_epics_fields(datatype).items():
            record.set_field(name, value)

    attribute.add_update_datatype_callback(datatype_updater)
    return record


def _create_and_link_command_pvs(pv_prefix: str, controller: Controller) -> None:
    for single_mapping in controller.get_controller_mappings():
        path = single_mapping.controller.path
        for attr_name, method in single_mapping.command_methods.items():
            pv_name = attr_name.title().replace("_", "")
            _pv_prefix = ":".join([pv_prefix] + path)
            if len(f"{_pv_prefix}:{pv_name}") > EPICS_MAX_NAME_LENGTH:
                print(
                    f"Not creating PV for {attr_name} as full name would exceed"
                    f" {EPICS_MAX_NAME_LENGTH} characters"
                )
                method.enabled = False
            else:
                _create_and_link_command_pv(
                    _pv_prefix,
                    pv_name,
                    attr_name,
                    MethodType(method.fn, single_mapping.controller),
                )


def _create_and_link_command_pv(
    pv_prefix: str, pv_name: str, attr_name: str, method: Callable
) -> None:
    async def wrapped_method(_: Any):
        await method()

    record = builder.Action(
        f"{pv_prefix}:{pv_name}",
        on_update=wrapped_method,
    )

    _add_attr_pvi_info(record, pv_prefix, attr_name, "x")


def _add_attr_pvi_info(
    record: RecordWrapper,
    prefix: str,
    name: str,
    access_mode: Literal["r", "w", "rw", "x"],
):
    """Add an info tag to a record to include it in the PVI for the controller.

    Args:
        record: Record to add info tag to
        prefix: PV prefix of controller
        name: Name of parameter to add to PVI
        access_mode: Access mode of parameter

    """
    record.add_info(
        "Q:group",
        {
            f"{prefix}:PVI": {
                f"value.{name}.{access_mode}": {
                    "+channel": "NAME",
                    "+type": "plain",
                    "+trigger": f"value.{name}.{access_mode}",
                }
            }
        },
    )
