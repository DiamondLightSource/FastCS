import enum
from typing import Any

import numpy as np
import pytest
from pytest_mock import MockerFixture
from softioc import softioc
from tests.assertable_controller import (
    AssertableControllerAPI,
    MyTestController,
    TestHandler,
    TestSetter,
    TestUpdater,
)
from tests.util import ColourEnum

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.controller_api import ControllerAPI
from fastcs.cs_methods import Command
from fastcs.datatypes import Bool, Enum, Float, Int, String, Waveform
from fastcs.exceptions import FastCSException
from fastcs.transport.epics.ca.adapter import EpicsCATransport
from fastcs.transport.epics.ca.ioc import (
    EPICS_MAX_NAME_LENGTH,
    EpicsCAIOC,
    _add_attr_pvi_info,
    _add_pvi_info,
    _add_sub_controller_pvi_info,
    _create_and_link_read_pv,
    _create_and_link_write_pv,
    _make_record,
)
from fastcs.transport.epics.ca.util import (
    record_metadata_from_attribute,
    record_metadata_from_datatype,
)

DEVICE = "DEVICE"

SEVENTEEN_VALUES = [str(i) for i in range(1, 18)]


class OnOffStates(enum.IntEnum):
    DISABLED = 0
    ENABLED = 1


@pytest.mark.asyncio
async def test_create_and_link_read_pv(mocker: MockerFixture):
    make_record = mocker.patch("fastcs.transport.epics.ca.ioc._make_record")
    add_attr_pvi_info = mocker.patch("fastcs.transport.epics.ca.ioc._add_attr_pvi_info")
    record = make_record.return_value

    attribute = AttrR(Int())
    attribute.add_update_callback = mocker.MagicMock()

    _create_and_link_read_pv("PREFIX", "PV", "attr", attribute)

    make_record.assert_called_once_with("PREFIX:PV", attribute)
    add_attr_pvi_info.assert_called_once_with(record, "PREFIX", "attr", "r")

    # Extract the callback generated and set in the function and call it
    attribute.add_update_callback.assert_called_once_with(mocker.ANY)
    record_set_callback = attribute.add_update_callback.call_args[0][0]
    await record_set_callback(1)

    record.set.assert_called_once_with(1)


@pytest.mark.parametrize(
    "attribute,record_type,kwargs",
    (
        (AttrR(String()), "longStringIn", {}),
        (
            AttrR(Enum(ColourEnum)),
            "mbbIn",
            {"ZRST": "RED", "ONST": "GREEN", "TWST": "BLUE"},
        ),
        (
            AttrR(Enum(enum.IntEnum("ONOFF_STATES", {"DISABLED": 0, "ENABLED": 1}))),
            "mbbIn",
            {"ZRST": "DISABLED", "ONST": "ENABLED"},
        ),
        (AttrR(Waveform(np.int32, (10,))), "WaveformIn", {}),
    ),
)
def test_make_input_record(
    attribute: AttrR,
    record_type: str,
    kwargs: dict[str, Any],
    mocker: MockerFixture,
):
    builder = mocker.patch("fastcs.transport.epics.ca.util.builder")

    pv = "PV"
    _make_record(pv, attribute)
    kwargs.update(record_metadata_from_datatype(attribute.datatype))
    kwargs.update(record_metadata_from_attribute(attribute))

    getattr(builder, record_type).assert_called_once_with(
        pv,
        **kwargs,
    )


def test_make_record_raises(mocker: MockerFixture):
    # Pass a mock as attribute to provoke the fallback case matching on datatype
    with pytest.raises(FastCSException):
        _make_record("PV", mocker.MagicMock())


@pytest.mark.asyncio
async def test_create_and_link_write_pv(mocker: MockerFixture):
    make_record = mocker.patch("fastcs.transport.epics.ca.ioc._make_record")
    add_attr_pvi_info = mocker.patch("fastcs.transport.epics.ca.ioc._add_attr_pvi_info")
    record = make_record.return_value

    attribute = AttrW(Int())
    attribute.process_without_display_update = mocker.AsyncMock()
    attribute.add_write_display_callback = mocker.MagicMock()

    _create_and_link_write_pv("PREFIX", "PV", "attr", attribute)

    make_record.assert_called_once_with(
        "PREFIX:PV", attribute, on_update=mocker.ANY, out_record=True
    )
    add_attr_pvi_info.assert_called_once_with(record, "PREFIX", "attr", "w")

    # Extract the write update callback generated and set in the function and call it
    attribute.add_write_display_callback.assert_called_once_with(mocker.ANY)
    write_display_callback = attribute.add_write_display_callback.call_args[0][0]
    await write_display_callback(1)

    record.set.assert_called_once_with(1, process=False)

    # Extract the on update callback generated and set in the function and call it
    on_update_callback = make_record.call_args[1]["on_update"]
    await on_update_callback(1)

    attribute.process_without_display_update.assert_called_once_with(1)


class LongEnum(enum.Enum):
    THIS = 0
    IS = 1
    AN = 2
    ENUM = 3
    WITH = 4
    ALTOGETHER = 5
    TOO = 6
    MANY = 7
    VALUES = 8
    TO = 9
    BE = 10
    DESCRIBED = 11
    BY = 12
    MBB = 14
    TYPE = 15
    EPICS = 16
    RECORDS = 17


@pytest.mark.parametrize(
    "attribute,record_type,kwargs",
    (
        (
            AttrW(Enum(enum.IntEnum("ONOFF_STATES", {"DISABLED": 0, "ENABLED": 1}))),
            "mbbOut",
            {"ZRST": "DISABLED", "ONST": "ENABLED"},
        ),
    ),
)
def test_make_output_record(
    attribute: AttrW,
    record_type: str,
    kwargs: dict[str, Any],
    mocker: MockerFixture,
):
    builder = mocker.patch("fastcs.transport.epics.ca.util.builder")
    update = mocker.MagicMock()

    pv = "PV"
    _make_record(pv, attribute, on_update=update, out_record=True)

    kwargs.update(record_metadata_from_datatype(attribute.datatype, out_record=True))
    kwargs.update(record_metadata_from_attribute(attribute))
    kwargs.update({"always_update": True, "on_update": update})

    getattr(builder, record_type).assert_called_once_with(
        pv,
        **kwargs,
    )


def test_long_enum_validator(mocker: MockerFixture):
    builder = mocker.patch("fastcs.transport.epics.ca.util.builder")
    update = mocker.MagicMock()
    attribute = AttrRW(Enum(LongEnum))
    pv = "PV"
    record = _make_record(pv, attribute, on_update=update, out_record=True)
    validator = builder.longStringOut.call_args.kwargs["validate"]
    assert validator(record, "THIS")  # value is one of the Enum names
    assert not validator(record, "an invalid string value")


def test_get_output_record_raises(mocker: MockerFixture):
    # Pass a mock as attribute to provoke the fallback case matching on datatype
    with pytest.raises(FastCSException):
        _make_record("PV", mocker.MagicMock(), on_update=mocker.MagicMock())


class EpicsController(MyTestController):
    read_int = AttrR(Int(), handler=TestUpdater())
    read_write_int = AttrRW(Int(), handler=TestHandler())
    read_write_float = AttrRW(Float())
    read_bool = AttrR(Bool())
    write_bool = AttrW(Bool(), handler=TestSetter())
    read_string = AttrRW(String())
    enum = AttrRW(Enum(enum.IntEnum("Enum", {"RED": 0, "GREEN": 1, "BLUE": 2})))
    one_d_waveform = AttrRW(Waveform(np.int32, (10,)))


@pytest.fixture()
def epics_controller_api(class_mocker: MockerFixture):
    return AssertableControllerAPI(EpicsController(), class_mocker)


def test_ioc(mocker: MockerFixture, epics_controller_api: ControllerAPI):
    ioc_builder = mocker.patch("fastcs.transport.epics.ca.ioc.builder")
    builder = mocker.patch("fastcs.transport.epics.ca.util.builder")
    add_pvi_info = mocker.patch("fastcs.transport.epics.ca.ioc._add_pvi_info")
    add_sub_controller_pvi_info = mocker.patch(
        "fastcs.transport.epics.ca.ioc._add_sub_controller_pvi_info"
    )

    EpicsCAIOC(DEVICE, epics_controller_api)

    # Check records are created
    builder.boolIn.assert_called_once_with(
        f"{DEVICE}:ReadBool",
        **record_metadata_from_attribute(epics_controller_api.attributes["read_bool"]),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["read_bool"].datatype
        ),
    )
    builder.longIn.assert_any_call(
        f"{DEVICE}:ReadInt",
        **record_metadata_from_attribute(epics_controller_api.attributes["read_int"]),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["read_int"].datatype
        ),
    )
    builder.aIn.assert_called_once_with(
        f"{DEVICE}:ReadWriteFloat_RBV",
        **record_metadata_from_attribute(
            epics_controller_api.attributes["read_write_float"]
        ),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["read_write_float"].datatype
        ),
    )
    builder.aOut.assert_any_call(
        f"{DEVICE}:ReadWriteFloat",
        always_update=True,
        on_update=mocker.ANY,
        **record_metadata_from_attribute(
            epics_controller_api.attributes["read_write_float"]
        ),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["read_write_float"].datatype,
            out_record=True,
        ),
    )
    builder.longIn.assert_any_call(
        f"{DEVICE}:ReadWriteInt_RBV",
        **record_metadata_from_attribute(
            epics_controller_api.attributes["read_write_int"]
        ),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["read_write_int"].datatype
        ),
    )
    builder.longOut.assert_called_with(
        f"{DEVICE}:ReadWriteInt",
        always_update=True,
        on_update=mocker.ANY,
        **record_metadata_from_attribute(
            epics_controller_api.attributes["read_write_int"]
        ),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["read_write_int"].datatype, out_record=True
        ),
    )
    builder.mbbIn.assert_called_once_with(
        f"{DEVICE}:Enum_RBV",
        **record_metadata_from_attribute(epics_controller_api.attributes["enum"]),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["enum"].datatype
        ),
    )
    builder.mbbOut.assert_called_once_with(
        f"{DEVICE}:Enum",
        always_update=True,
        on_update=mocker.ANY,
        **record_metadata_from_attribute(epics_controller_api.attributes["enum"]),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["enum"].datatype, out_record=True
        ),
    )
    builder.boolOut.assert_called_once_with(
        f"{DEVICE}:WriteBool",
        always_update=True,
        on_update=mocker.ANY,
        **record_metadata_from_attribute(epics_controller_api.attributes["write_bool"]),
        **record_metadata_from_datatype(
            epics_controller_api.attributes["write_bool"].datatype, out_record=True
        ),
    )
    ioc_builder.Action.assert_any_call(
        f"{DEVICE}:Go", on_update=mocker.ANY, blocking=True
    )

    # Check info tags are added
    add_pvi_info.assert_called_once_with(f"{DEVICE}:PVI")
    add_sub_controller_pvi_info.assert_called_once_with(DEVICE, epics_controller_api)


def test_add_pvi_info(mocker: MockerFixture):
    builder = mocker.patch("fastcs.transport.epics.ca.ioc.builder")
    controller = mocker.MagicMock()
    controller.path = []
    child = mocker.MagicMock()
    child.path = ["Child"]
    controller.get_sub_controllers.return_value = {"d": child}

    _add_pvi_info(f"{DEVICE}:PVI")

    builder.longStringIn.assert_called_once_with(
        f"{DEVICE}:PVI_PV",
        initial_value=f"{DEVICE}:PVI",
        DESC="The records in this controller",
    )
    record = builder.longStringIn.return_value
    record.add_info.assert_called_once_with(
        "Q:group",
        {
            f"{DEVICE}:PVI": {
                "+id": "epics:nt/NTPVI:1.0",
                "display.description": {"+type": "plain", "+channel": "DESC"},
                "": {"+type": "meta", "+channel": "VAL"},
            }
        },
    )


def test_add_pvi_info_with_parent(mocker: MockerFixture):
    builder = mocker.patch("fastcs.transport.epics.ca.ioc.builder")
    controller = mocker.MagicMock()
    controller.path = []
    child = mocker.MagicMock()
    child.path = ["Child"]
    controller.get_sub_controllers.return_value = {"d": child}

    child = mocker.MagicMock()
    _add_pvi_info(f"{DEVICE}:Child:PVI", f"{DEVICE}:PVI", "child")

    builder.longStringIn.assert_called_once_with(
        f"{DEVICE}:Child:PVI_PV",
        initial_value=f"{DEVICE}:Child:PVI",
        DESC="The records in this controller",
    )
    record = builder.longStringIn.return_value
    record.add_info.assert_called_once_with(
        "Q:group",
        {
            f"{DEVICE}:Child:PVI": {
                "+id": "epics:nt/NTPVI:1.0",
                "display.description": {"+type": "plain", "+channel": "DESC"},
                "": {"+type": "meta", "+channel": "VAL"},
            },
            f"{DEVICE}:PVI": {
                "value.child.d": {
                    "+channel": "VAL",
                    "+type": "plain",
                    "+trigger": "value.child.d",
                }
            },
        },
    )


def test_add_sub_controller_pvi_info(mocker: MockerFixture):
    add_pvi_info = mocker.patch("fastcs.transport.epics.ca.ioc._add_pvi_info")
    parent_api = mocker.MagicMock()
    parent_api.path = []
    child_api = mocker.MagicMock()
    child_api.path = ["Child"]
    parent_api.sub_apis = {"d": child_api}

    _add_sub_controller_pvi_info(DEVICE, parent_api)

    add_pvi_info.assert_called_once_with(
        f"{DEVICE}:Child:PVI", f"{DEVICE}:PVI", "child"
    )


def test_add_attr_pvi_info(mocker: MockerFixture):
    record = mocker.MagicMock()

    _add_attr_pvi_info(record, DEVICE, "attr", "r")

    record.add_info.assert_called_once_with(
        "Q:group",
        {
            f"{DEVICE}:PVI": {
                "value.attr.r": {
                    "+channel": "NAME",
                    "+type": "plain",
                    "+trigger": "value.attr.r",
                }
            }
        },
    )


async def do_nothing(): ...


class ControllerLongNames(Controller):
    attr_r_with_reallyreallyreallyreallyreallyreallyreally_long_name = AttrR(Int())
    attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV = AttrRW(Int())
    attr_rw_short_name = AttrRW(Int())
    command_with_reallyreallyreallyreallyreallyreallyreally_long_name = Command(
        do_nothing
    )
    command_short_name = Command(do_nothing)


def test_long_pv_names_discarded(mocker: MockerFixture):
    ioc_builder = mocker.patch("fastcs.transport.epics.ca.ioc.builder")
    builder = mocker.patch("fastcs.transport.epics.ca.util.builder")
    long_name_controller_api = AssertableControllerAPI(ControllerLongNames(), mocker)
    long_attr_name = "attr_r_with_reallyreallyreallyreallyreallyreallyreally_long_name"
    long_rw_name = "attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV"
    assert long_name_controller_api.attributes["attr_rw_short_name"].enabled
    assert long_name_controller_api.attributes[long_attr_name].enabled
    EpicsCAIOC(DEVICE, long_name_controller_api)
    assert long_name_controller_api.attributes["attr_rw_short_name"].enabled
    assert not long_name_controller_api.attributes[long_attr_name].enabled

    short_pv_name = "attr_rw_short_name".title().replace("_", "")
    builder.longOut.assert_called_once_with(
        f"{DEVICE}:{short_pv_name}",
        always_update=True,
        on_update=mocker.ANY,
        **record_metadata_from_datatype(
            long_name_controller_api.attributes["attr_rw_short_name"].datatype,
            out_record=True,
        ),
        **record_metadata_from_attribute(
            long_name_controller_api.attributes["attr_rw_short_name"]
        ),
    )
    builder.longIn.assert_called_once_with(
        f"{DEVICE}:{short_pv_name}_RBV",
        **record_metadata_from_datatype(
            long_name_controller_api.attributes[
                "attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV"
            ].datatype
        ),
        **record_metadata_from_attribute(
            long_name_controller_api.attributes[
                "attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV"
            ]
        ),
    )

    long_pv_name = long_attr_name.title().replace("_", "")
    with pytest.raises(AssertionError):
        builder.longIn.assert_called_once_with(f"{DEVICE}:{long_pv_name}")

    long_rw_pv_name = long_rw_name.title().replace("_", "")
    # neither the readback nor setpoint PV gets made if the full pv name with _RBV
    # suffix is too long
    assert (
        EPICS_MAX_NAME_LENGTH - 4
        < len(f"{DEVICE}:{long_rw_pv_name}")
        < EPICS_MAX_NAME_LENGTH
    )

    with pytest.raises(AssertionError):
        builder.longOut.assert_called_once_with(
            f"{DEVICE}:{long_rw_pv_name}",
            always_update=True,
            on_update=mocker.ANY,
        )
    with pytest.raises(AssertionError):
        builder.longIn.assert_called_once_with(f"{DEVICE}:{long_rw_pv_name}_RBV")

    assert long_name_controller_api.command_methods["command_short_name"].enabled
    long_command_name = (
        "command_with_reallyreallyreallyreallyreallyreallyreally_long_name"
    )
    assert not long_name_controller_api.command_methods[long_command_name].enabled

    short_command_pv_name = "command_short_name".title().replace("_", "")
    ioc_builder.Action.assert_called_once_with(
        f"{DEVICE}:{short_command_pv_name}", on_update=mocker.ANY, blocking=True
    )
    with pytest.raises(AssertionError):
        long_command_pv_name = long_command_name.title().replace("_", "")
        builder.aOut.assert_called_once_with(
            f"{DEVICE}:{long_command_pv_name}",
            initial_value=0,
            always_update=True,
            on_update=mocker.ANY,
        )


def test_update_datatype(mocker: MockerFixture):
    builder = mocker.patch("fastcs.transport.epics.ca.util.builder")

    pv_name = f"{DEVICE}:Attr"

    attr_r = AttrR(Int())
    record_r = _make_record(pv_name, attr_r)

    builder.longIn.assert_called_once_with(
        pv_name,
        **record_metadata_from_attribute(attr_r),
        **record_metadata_from_datatype(attr_r.datatype),
    )
    record_r.set_field.assert_not_called()
    attr_r.update_datatype(Int(units="m", min_alarm=-3))
    record_r.set_field.assert_any_call("EGU", "m")
    record_r.set_field.assert_any_call("LOPR", -3)

    with pytest.raises(
        ValueError,
        match="Attribute datatype must be of type <class 'fastcs.datatypes.Int'>",
    ):
        attr_r.update_datatype(String())  # type: ignore

    attr_w = AttrW(Int())
    record_w = _make_record(pv_name, attr_w, on_update=mocker.ANY, out_record=True)

    builder.longIn.assert_called_once_with(
        pv_name,
        **record_metadata_from_attribute(attr_w),
        **record_metadata_from_datatype(attr_w.datatype),
    )
    record_w.set_field.assert_not_called()
    attr_w.update_datatype(Int(units="m", min_alarm=-1, min=-3))
    record_w.set_field.assert_any_call("EGU", "m")
    record_w.set_field.assert_any_call("LOPR", -1)
    record_w.set_field.assert_any_call("DRVL", -3)

    with pytest.raises(
        ValueError,
        match="Attribute datatype must be of type <class 'fastcs.datatypes.Int'>",
    ):
        attr_w.update_datatype(String())  # type: ignore


def test_ca_context_contains_softioc_commands(mocker: MockerFixture):
    transport = EpicsCATransport(mocker.MagicMock(), mocker.MagicMock())

    softioc_commands = {
        command: getattr(softioc, command) for command in softioc.command_names
    }
    # We exclude "exit" from the context
    softioc_commands.pop("exit")

    assert transport.context == softioc_commands
