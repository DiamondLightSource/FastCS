from typing import Any

import pytest
from pytest_mock import MockerFixture

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.backends.epics.ioc import (
    EPICS_MAX_NAME_LENGTH,
    EpicsIOC,
    _add_attr_pvi_info,
    _add_pvi_info,
    _add_sub_controller_pvi_info,
    _create_and_link_read_pv,
    _create_and_link_write_pv,
    _get_input_record,
    _get_output_record,
)
from fastcs.controller import Controller
from fastcs.cs_methods import Command
from fastcs.datatypes import Int, String
from fastcs.exceptions import FastCSException
from fastcs.mapping import Mapping

DEVICE = "DEVICE"

SEVENTEEN_VALUES = [str(i) for i in range(1, 18)]
ONOFF_STATES = {"ZRST": "disabled", "ONST": "enabled"}


@pytest.mark.asyncio
async def test_create_and_link_read_pv(mocker: MockerFixture):
    get_input_record = mocker.patch("fastcs.backends.epics.ioc._get_input_record")
    add_attr_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_attr_pvi_info")
    attr_is_enum = mocker.patch("fastcs.backends.epics.ioc.attr_is_enum")
    record = get_input_record.return_value

    attribute = mocker.MagicMock()

    attr_is_enum.return_value = False
    _create_and_link_read_pv("PREFIX", "PV", "attr", attribute)

    get_input_record.assert_called_once_with("PREFIX:PV", attribute)
    add_attr_pvi_info.assert_called_once_with(record, "PREFIX", "attr", "r")

    # Extract the callback generated and set in the function and call it
    attribute.set_update_callback.assert_called_once_with(mocker.ANY)
    record_set_callback = attribute.set_update_callback.call_args[0][0]
    await record_set_callback(1)

    record.set.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_create_and_link_read_pv_enum(mocker: MockerFixture):
    get_input_record = mocker.patch("fastcs.backends.epics.ioc._get_input_record")
    add_attr_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_attr_pvi_info")
    attr_is_enum = mocker.patch("fastcs.backends.epics.ioc.attr_is_enum")
    record = get_input_record.return_value
    enum_value_to_index = mocker.patch("fastcs.backends.epics.ioc.enum_value_to_index")

    attribute = mocker.MagicMock()

    attr_is_enum.return_value = True
    _create_and_link_read_pv("PREFIX", "PV", "attr", attribute)

    get_input_record.assert_called_once_with("PREFIX:PV", attribute)
    add_attr_pvi_info.assert_called_once_with(record, "PREFIX", "attr", "r")

    # Extract the callback generated and set in the function and call it
    attribute.set_update_callback.assert_called_once_with(mocker.ANY)
    record_set_callback = attribute.set_update_callback.call_args[0][0]
    await record_set_callback(1)

    enum_value_to_index.assert_called_once_with(attribute, 1)
    record.set.assert_called_once_with(enum_value_to_index.return_value)


@pytest.mark.parametrize(
    "attribute,record_type,kwargs",
    (
        (AttrR(String()), "longStringIn", {}),
        (
            AttrR(String(), allowed_values=list(ONOFF_STATES.values())),
            "mbbIn",
            ONOFF_STATES,
        ),
        (AttrR(String(), allowed_values=SEVENTEEN_VALUES), "longStringIn", {}),
    ),
)
def test_get_input_record(
    attribute: AttrR,
    record_type: str,
    kwargs: dict[str, Any],
    mocker: MockerFixture,
):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")

    pv = "PV"
    _get_input_record(pv, attribute)

    getattr(builder, record_type).assert_called_once_with(pv, **kwargs)


def test_get_input_record_raises(mocker: MockerFixture):
    # Pass a mock as attribute to provoke the fallback case matching on datatype
    with pytest.raises(FastCSException):
        _get_input_record("PV", mocker.MagicMock())


@pytest.mark.asyncio
async def test_create_and_link_write_pv(mocker: MockerFixture):
    get_output_record = mocker.patch("fastcs.backends.epics.ioc._get_output_record")
    add_attr_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_attr_pvi_info")
    attr_is_enum = mocker.patch("fastcs.backends.epics.ioc.attr_is_enum")
    record = get_output_record.return_value

    attribute = mocker.MagicMock()
    attribute.process_without_display_update = mocker.AsyncMock()

    attr_is_enum.return_value = False
    _create_and_link_write_pv("PREFIX", "PV", "attr", attribute)

    get_output_record.assert_called_once_with(
        "PREFIX:PV", attribute, on_update=mocker.ANY
    )
    add_attr_pvi_info.assert_called_once_with(record, "PREFIX", "attr", "w")

    # Extract the write update callback generated and set in the function and call it
    attribute.set_write_display_callback.assert_called_once_with(mocker.ANY)
    write_display_callback = attribute.set_write_display_callback.call_args[0][0]
    await write_display_callback(1)

    record.set.assert_called_once_with(1, process=False)

    # Extract the on update callback generated and set in the function and call it
    on_update_callback = get_output_record.call_args[1]["on_update"]
    await on_update_callback(1)

    attribute.process_without_display_update.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_create_and_link_write_pv_enum(mocker: MockerFixture):
    get_output_record = mocker.patch("fastcs.backends.epics.ioc._get_output_record")
    add_attr_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_attr_pvi_info")
    attr_is_enum = mocker.patch("fastcs.backends.epics.ioc.attr_is_enum")
    enum_value_to_index = mocker.patch("fastcs.backends.epics.ioc.enum_value_to_index")
    enum_index_to_value = mocker.patch("fastcs.backends.epics.ioc.enum_index_to_value")
    record = get_output_record.return_value

    attribute = mocker.MagicMock()
    attribute.process_without_display_update = mocker.AsyncMock()

    attr_is_enum.return_value = True
    _create_and_link_write_pv("PREFIX", "PV", "attr", attribute)

    get_output_record.assert_called_once_with(
        "PREFIX:PV", attribute, on_update=mocker.ANY
    )
    add_attr_pvi_info.assert_called_once_with(record, "PREFIX", "attr", "w")

    # Extract the write update callback generated and set in the function and call it
    attribute.set_write_display_callback.assert_called_once_with(mocker.ANY)
    write_display_callback = attribute.set_write_display_callback.call_args[0][0]
    await write_display_callback(1)

    enum_value_to_index.assert_called_once_with(attribute, 1)
    record.set.assert_called_once_with(enum_value_to_index.return_value, process=False)

    # Extract the on update callback generated and set in the function and call it
    on_update_callback = get_output_record.call_args[1]["on_update"]
    await on_update_callback(1)

    attribute.process_without_display_update.assert_called_once_with(
        enum_index_to_value.return_value
    )


@pytest.mark.parametrize(
    "attribute,record_type,kwargs",
    (
        (AttrR(String()), "longStringOut", {}),
        (
            AttrR(String(), allowed_values=list(ONOFF_STATES.values())),
            "mbbOut",
            ONOFF_STATES,
        ),
        (AttrR(String(), allowed_values=SEVENTEEN_VALUES), "longStringOut", {}),
    ),
)
def test_get_output_record(
    attribute: AttrW,
    record_type: str,
    kwargs: dict[str, Any],
    mocker: MockerFixture,
):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
    update = mocker.MagicMock()

    pv = "PV"
    _get_output_record(pv, attribute, on_update=update)

    getattr(builder, record_type).assert_called_once_with(
        pv, always_update=True, on_update=update, **kwargs
    )


def test_get_output_record_raises(mocker: MockerFixture):
    # Pass a mock as attribute to provoke the fallback case matching on datatype
    with pytest.raises(FastCSException):
        _get_output_record("PV", mocker.MagicMock(), on_update=mocker.MagicMock())


def test_ioc(mocker: MockerFixture, mapping: Mapping):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
    add_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_pvi_info")
    add_sub_controller_pvi_info = mocker.patch(
        "fastcs.backends.epics.ioc._add_sub_controller_pvi_info"
    )

    EpicsIOC(DEVICE, mapping)

    # Check records are created
    builder.boolIn.assert_called_once_with(f"{DEVICE}:ReadBool", ZNAM="OFF", ONAM="ON")
    builder.longIn.assert_any_call(f"{DEVICE}:ReadInt")
    builder.aIn.assert_called_once_with(f"{DEVICE}:ReadWriteFloat_RBV", PREC=2)
    builder.aOut.assert_any_call(
        f"{DEVICE}:ReadWriteFloat", always_update=True, on_update=mocker.ANY, PREC=2
    )
    builder.longIn.assert_any_call(f"{DEVICE}:BigEnum")
    builder.longIn.assert_any_call(f"{DEVICE}:ReadWriteInt_RBV")
    builder.longOut.assert_called_with(
        f"{DEVICE}:ReadWriteInt", always_update=True, on_update=mocker.ANY
    )
    builder.mbbIn.assert_called_once_with(
        f"{DEVICE}:StringEnum_RBV", ZRST="red", ONST="green", TWST="blue"
    )
    builder.mbbOut.assert_called_once_with(
        f"{DEVICE}:StringEnum",
        ZRST="red",
        ONST="green",
        TWST="blue",
        always_update=True,
        on_update=mocker.ANY,
    )
    builder.boolOut.assert_called_once_with(
        f"{DEVICE}:WriteBool",
        ZNAM="OFF",
        ONAM="ON",
        always_update=True,
        on_update=mocker.ANY,
    )
    builder.aOut.assert_any_call(
        f"{DEVICE}:Go", initial_value=0, always_update=True, on_update=mocker.ANY
    )

    # Check info tags are added
    add_pvi_info.assert_called_once_with(f"{DEVICE}:PVI")
    add_sub_controller_pvi_info.assert_called_once_with(DEVICE, mapping.controller)


def test_add_pvi_info(mocker: MockerFixture):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
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
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
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
    add_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_pvi_info")
    controller = mocker.MagicMock()
    controller.path = []
    child = mocker.MagicMock()
    child.path = ["Child"]
    controller.get_sub_controllers.return_value = {"d": child}

    _add_sub_controller_pvi_info(DEVICE, controller)

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


async def do_nothing(arg): ...


class NothingCommand:
    def __init__(self):  # make fastcs_method instance variable
        self.fastcs_method = Command(do_nothing)


class ControllerLongNames(Controller):
    attr_r_with_reallyreallyreallyreallyreallyreallyreally_long_name = AttrR(Int())
    attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV = AttrRW(Int())
    attr_rw_short_name = AttrRW(Int())
    command_with_reallyreallyreallyreallyreallyreallyreally_long_name = NothingCommand()
    command_short_name = NothingCommand()


def test_long_pv_names_discarded(mocker: MockerFixture):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
    long_name_controller = ControllerLongNames()
    long_name_mapping = Mapping(long_name_controller)
    long_attr_name = "attr_r_with_reallyreallyreallyreallyreallyreallyreally_long_name"
    long_rw_name = "attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV"
    assert long_name_controller.attr_rw_short_name.enabled
    assert getattr(long_name_controller, long_attr_name).enabled
    EpicsIOC(DEVICE, long_name_mapping)
    assert long_name_controller.attr_rw_short_name.enabled
    assert not getattr(long_name_controller, long_attr_name).enabled

    short_pv_name = "attr_rw_short_name".title().replace("_", "")
    builder.longOut.assert_called_once_with(
        f"{DEVICE}:{short_pv_name}",
        always_update=True,
        on_update=mocker.ANY,
    )
    builder.longIn.assert_called_once_with(
        f"{DEVICE}:{short_pv_name}_RBV",
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

    assert long_name_controller.command_short_name.fastcs_method.enabled
    long_command_name = (
        "command_with_" "reallyreallyreallyreallyreallyreallyreally_long_name"
    )
    assert not getattr(long_name_controller, long_command_name).fastcs_method.enabled

    short_command_pv_name = "command_short_name".title().replace("_", "")
    builder.aOut.assert_called_once_with(
        f"{DEVICE}:{short_command_pv_name}",
        initial_value=0,
        always_update=True,
        on_update=mocker.ANY,
    )
    with pytest.raises(AssertionError):
        long_command_pv_name = long_command_name.title().replace("_", "")
        builder.aOut.assert_called_once_with(
            f"{DEVICE}:{long_command_pv_name}",
            initial_value=0,
            always_update=True,
            on_update=mocker.ANY,
        )
