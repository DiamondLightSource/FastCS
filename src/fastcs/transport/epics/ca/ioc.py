import asyncio
from collections.abc import Callable
from typing import Any, Literal

from softioc import builder, softioc
from softioc.asyncio_dispatcher import AsyncioDispatcher
from softioc.pythonSoftIoc import RecordWrapper

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.cs_methods import Command
from fastcs.datatypes import DataType, T
from fastcs.logging import bind_logger
from fastcs.tracer import Tracer
from fastcs.transport.epics.ca.util import (
    builder_callable_from_attribute,
    cast_from_epics_type,
    cast_to_epics_type,
    record_metadata_from_attribute,
    record_metadata_from_datatype,
)
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.transport.epics.util import controller_pv_prefix
from fastcs.util import snake_to_pascal

EPICS_MAX_NAME_LENGTH = 60


tracer = Tracer(name=__name__)
logger = bind_logger(logger_name=__name__)


class EpicsCAIOC:
    """A softioc which handles a controller"""

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
    parent_pvi = f"{controller_pv_prefix(pv_prefix, parent)}:PVI"

    for child in parent.sub_apis.values():
        child_pvi = f"{controller_pv_prefix(pv_prefix, child)}:PVI"
        child_name = (
            f"__{child.path[-1]}"  # Sub-Controller of ControllerVector
            if child.path[-1].isdigit()
            else child.path[-1]
        )

        _add_pvi_info(child_pvi, parent_pvi, child_name.lower())

        _add_sub_controller_pvi_info(pv_prefix, child)


def _create_and_link_attribute_pvs(
    root_pv_prefix: str, root_controller_api: ControllerAPI
) -> None:
    for controller_api in root_controller_api.walk_api():
        pv_prefix = controller_pv_prefix(root_pv_prefix, controller_api)

        for attr_name, attribute in controller_api.attributes.items():
            pv_name = snake_to_pascal(attr_name)

            full_pv_name_length = len(f"{pv_prefix}:{pv_name}")
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
                            pv_prefix, f"{pv_name}_RBV", attr_name, attribute
                        )
                        _create_and_link_write_pv(
                            pv_prefix, pv_name, attr_name, attribute
                        )
                case AttrR():
                    _create_and_link_read_pv(pv_prefix, pv_name, attr_name, attribute)
                case AttrW():
                    _create_and_link_write_pv(pv_prefix, pv_name, attr_name, attribute)


def _create_and_link_read_pv(
    pv_prefix: str, pv_name: str, attr_name: str, attribute: AttrR[T]
) -> None:
    pv = f"{pv_prefix}:{pv_name}"

    async def async_record_set(value: T):
        tracer.log_event("PV set from attribute", topic=attribute, pv=pv, value=value)

        record.set(cast_to_epics_type(attribute.datatype, value))

    record = _make_record(pv, attribute)
    _add_attr_pvi_info(record, pv_prefix, attr_name, "r")

    attribute.add_on_update_callback(async_record_set)


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
        for name, value in record_metadata_from_datatype(datatype, out_record).items():
            record.set_field(name, value)

    attribute.add_update_datatype_callback(datatype_updater)
    return record


def _create_and_link_write_pv(
    pv_prefix: str, pv_name: str, attr_name: str, attribute: AttrW[T]
) -> None:
    pv = f"{pv_prefix}:{pv_name}"

    async def on_update(value):
        logger.info("PV put: {pv} = {value}", pv=pv, value=value)

        await attribute.put(cast_from_epics_type(attribute.datatype, value))

    async def set_setpoint_without_process(value: T):
        tracer.log_event(
            "PV setpoint set from attribute", topic=attribute, pv=pv, value=value
        )

        record.set(cast_to_epics_type(attribute.datatype, value), process=False)

    record = _make_record(pv, attribute, on_update=on_update, out_record=True)

    _add_attr_pvi_info(record, pv_prefix, attr_name, "w")

    attribute.add_sync_setpoint_callback(set_setpoint_without_process)


def _create_and_link_command_pvs(
    root_pv_prefix: str, root_controller_api: ControllerAPI
) -> None:
    for controller_api in root_controller_api.walk_api():
        pv_prefix = controller_pv_prefix(root_pv_prefix, controller_api)

        for attr_name, method in controller_api.command_methods.items():
            pv_name = snake_to_pascal(attr_name)

            if len(f"{pv_prefix}:{pv_name}") > EPICS_MAX_NAME_LENGTH:
                print(
                    f"Not creating PV for {attr_name} as full name would exceed"
                    f" {EPICS_MAX_NAME_LENGTH} characters"
                )
                method.enabled = False
            else:
                _create_and_link_command_pv(
                    pv_prefix,
                    pv_name,
                    attr_name,
                    method,
                )


def _create_and_link_command_pv(
    pv_prefix: str, pv_name: str, attr_name: str, method: Command
) -> None:
    pv = f"{pv_prefix}:{pv_name}"

    async def wrapped_method(_: Any):
        tracer.log_event("Command PV put", topic=method, pv=pv)

        await method.fn()

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
