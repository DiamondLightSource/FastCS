import pytest
from pytest_mock import MockerFixture

from fastcs.attributes import AttrR, AttrRW
from fastcs.backends.epics.ioc import (
    EPICS_MAX_NAME_LENGTH,
    EpicsIOC,
    _add_attr_pvi_info,
    _add_pvi_info,
    _add_sub_controller_pvi_info,
)
from fastcs.controller import Controller
from fastcs.datatypes import Int
from fastcs.mapping import Mapping

DEVICE = "DEVICE"


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
    builder.longIn.assert_any_call(f"{DEVICE}:ReadWriteInt_RBV")
    builder.longOut.assert_called_with(
        f"{DEVICE}:ReadWriteInt", always_update=True, on_update=mocker.ANY
    )
    builder.longStringIn.assert_called_once_with(f"{DEVICE}:StringEnum_RBV")
    builder.longStringOut.assert_called_once_with(
        f"{DEVICE}:StringEnum", always_update=True, on_update=mocker.ANY
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


class ControllerLongNames(Controller):
    attr_r_with_reallyreallyreallyreallyreallyreallyreally_long_name = AttrR(Int())
    attr_rw_with_a_reallyreally_long_name_that_is_too_long_for_RBV = AttrRW(Int())
    attr_rw_short_name = AttrRW(Int())


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
        builder.longIn.assert_called_once_with(f"{DEVICE}:{long_rw_pv_name}_RBV")
