import asyncio
from collections.abc import Callable
from typing import Any, Literal

from softioc import builder, softioc
from softioc.asyncio_dispatcher import AsyncioDispatcher
from softioc.pythonSoftIoc import RecordWrapper

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.datatypes import DataType, T
from fastcs.transport.epics.ca.util import (
    builder_callable_from_attribute,
    cast_from_epics_type,
    cast_to_epics_type,
    record_metadata_from_attribute,
    record_metadata_from_datatype,
)
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.util import snake_to_pascal

EPICS_MAX_NAME_LENGTH = 60


class EpicsCAIOC:
    """A softioc which handles a controller.

    Avoid running directly, instead use `fastcs.launch.FastCS`.
    """

    def __init__(
        self,
        pv_prefix: str,
        controller_api: ControllerAPI,
        options: EpicsIOCOptions | None = None,
    ):
        self._options = options or EpicsIOCOptions()
        self._controller_api = controller_api
        _add_pvi_info(f"{pv_prefix}:PVI")
        _add_sub_controller_pvi_info(pv_prefix, controller_api)

        _create_and_link_attribute_pvs(pv_prefix, controller_api)
        _create_and_link_command_pvs(pv_prefix, controller_api)

    def run(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        dispatcher = AsyncioDispatcher(loop)  # Needs running loop
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)


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


def _add_sub_controller_pvi_info(pv_prefix: str, parent: ControllerAPI):
    """Add PVI references from controller to its sub controllers, recursively.

    Args:
        pv_prefix: PV Prefix of IOC
        parent: Controller to add PVI refs for

    """
    parent_pvi = ":".join([pv_prefix] + parent.path + ["PVI"])

    for child in parent.sub_apis.values():
        child_pvi = ":".join([pv_prefix] + child.path + ["PVI"])
        child_name = child.path[-1].lower()

        _add_pvi_info(child_pvi, parent_pvi, child_name)

        _add_sub_controller_pvi_info(pv_prefix, child)


def _create_and_link_attribute_pvs(
    pv_prefix: str, root_controller_api: ControllerAPI
) -> None:
    for controller_api in root_controller_api.walk_api():
        path = controller_api.path
        for attr_name, attribute in controller_api.attributes.items():
            pv_name = snake_to_pascal(attr_name)
            _pv_prefix = ":".join([pv_prefix] + path)
            full_pv_name_length = len(f"{_pv_prefix}:{pv_name}")

            if full_pv_name_length > EPICS_MAX_NAME_LENGTH:
                attribute.enabled = False
                print(
                    f"Not creating PV for {attr_name} for controller"
                    f" {controller_api.path} as full name would exceed"
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
    async def async_record_set(value: T):
        record.set(cast_to_epics_type(attribute.datatype, value))

    record = _make_record(f"{pv_prefix}:{pv_name}", attribute)
    _add_attr_pvi_info(record, pv_prefix, attr_name, "r")

    attribute.add_update_callback(async_record_set)


def _make_record(
    pv: str,
    attribute: AttrR | AttrW | AttrRW,
    on_update: Callable | None = None,
    out_record: bool = False,
) -> RecordWrapper:
    builder_callable = builder_callable_from_attribute(attribute, on_update is None)
    datatype_record_metadata = record_metadata_from_datatype(
        attribute.datatype, out_record
    )
    attribute_record_metadata = record_metadata_from_attribute(attribute)

    update = {"always_update": True, "on_update": on_update} if on_update else {}

    record = builder_callable(
        pv, **update, **datatype_record_metadata, **attribute_record_metadata
    )

    def datatype_updater(datatype: DataType):
        for name, value in record_metadata_from_datatype(datatype).items():
            record.set_field(name, value)

    attribute.add_update_datatype_callback(datatype_updater)
    return record


def _create_and_link_write_pv(
    pv_prefix: str, pv_name: str, attr_name: str, attribute: AttrW[T]
) -> None:
    async def on_update(value):
        await attribute.process_without_display_update(
            cast_from_epics_type(attribute.datatype, value)
        )

    async def async_write_display(value: T):
        record.set(cast_to_epics_type(attribute.datatype, value), process=False)

    record = _make_record(
        f"{pv_prefix}:{pv_name}", attribute, on_update=on_update, out_record=True
    )

    _add_attr_pvi_info(record, pv_prefix, attr_name, "w")

    attribute.add_write_display_callback(async_write_display)


def _create_and_link_command_pvs(
    pv_prefix: str, root_controller_api: ControllerAPI
) -> None:
    for controller_api in root_controller_api.walk_api():
        path = controller_api.path
        for attr_name, method in controller_api.command_methods.items():
            pv_name = snake_to_pascal(attr_name)
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
                    method.fn,
                )


def _create_and_link_command_pv(
    pv_prefix: str, pv_name: str, attr_name: str, method: Callable
) -> None:
    async def wrapped_method(_: Any):
        await method()

    record = builder.Action(
        f"{pv_prefix}:{pv_name}",
        on_update=wrapped_method,
        blocking=True,
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
