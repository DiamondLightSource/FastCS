from pytest_mock import MockerFixture

from fastcs.backends.epics.ioc import (
    EpicsIOC,
    _add_attr_pvi_info,
    _add_pvi_info,
    _add_sub_controller_pvi_info,
)
from fastcs.mapping import Mapping


def test_ioc(mocker: MockerFixture, mapping: Mapping):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
    add_pvi_info = mocker.patch("fastcs.backends.epics.ioc._add_pvi_info")
    add_sub_controller_pvi_info = mocker.patch(
        "fastcs.backends.epics.ioc._add_sub_controller_pvi_info"
    )

    EpicsIOC("DEVICE", mapping)

    # Check records are created
    builder.boolIn.assert_called_once_with("DEVICE:ReadBool", ZNAM="OFF", ONAM="ON")
    builder.longIn.assert_any_call("DEVICE:ReadInt")
    builder.aIn.assert_called_once_with("DEVICE:ReadWriteFloat_RBV", PREC=2)
    builder.aOut.assert_any_call(
        "DEVICE:ReadWriteFloat", always_update=True, on_update=mocker.ANY, PREC=2
    )
    builder.longIn.assert_any_call("DEVICE:ReadWriteInt_RBV")
    builder.longOut.assert_called_with(
        "DEVICE:ReadWriteInt", always_update=True, on_update=mocker.ANY
    )
    builder.longStringIn.assert_called_once_with("DEVICE:StringEnum_RBV")
    builder.longStringOut.assert_called_once_with(
        "DEVICE:StringEnum", always_update=True, on_update=mocker.ANY
    )
    builder.boolOut.assert_called_once_with(
        "DEVICE:WriteBool",
        ZNAM="OFF",
        ONAM="ON",
        always_update=True,
        on_update=mocker.ANY,
    )
    builder.aOut.assert_any_call(
        "DEVICE:Go", initial_value=0, always_update=True, on_update=mocker.ANY
    )

    # Check info tags are added
    add_pvi_info.assert_called_once_with("DEVICE:PVI")
    add_sub_controller_pvi_info.assert_called_once_with("DEVICE", mapping.controller)


def test_add_pvi_info(mocker: MockerFixture):
    builder = mocker.patch("fastcs.backends.epics.ioc.builder")
    controller = mocker.MagicMock()
    controller.path = []
    child = mocker.MagicMock()
    child.path = ["Child"]
    controller.get_sub_controllers.return_value = {"d": child}

    _add_pvi_info("DEVICE:PVI")

    builder.longStringIn.assert_called_once_with(
        "DEVICE:PVI_PV",
        initial_value="DEVICE:PVI",
        DESC="The records in this controller",
    )
    record = builder.longStringIn.return_value
    record.add_info.assert_called_once_with(
        "Q:group",
        {
            "DEVICE:PVI": {
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
    _add_pvi_info("DEVICE:Child:PVI", "DEVICE:PVI", "child")

    builder.longStringIn.assert_called_once_with(
        "DEVICE:Child:PVI_PV",
        initial_value="DEVICE:Child:PVI",
        DESC="The records in this controller",
    )
    record = builder.longStringIn.return_value
    record.add_info.assert_called_once_with(
        "Q:group",
        {
            "DEVICE:Child:PVI": {
                "+id": "epics:nt/NTPVI:1.0",
                "display.description": {"+type": "plain", "+channel": "DESC"},
                "": {"+type": "meta", "+channel": "VAL"},
            },
            "DEVICE:PVI": {
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

    _add_sub_controller_pvi_info("DEVICE", controller)

    add_pvi_info.assert_called_once_with("DEVICE:Child:PVI", "DEVICE:PVI", "child")


def test_add_attr_pvi_info(mocker: MockerFixture):
    record = mocker.MagicMock()

    _add_attr_pvi_info(record, "DEVICE", "attr", "r")

    record.add_info.assert_called_once_with(
        "Q:group",
        {
            "DEVICE:PVI": {
                "value.attr.r": {
                    "+channel": "NAME",
                    "+type": "plain",
                    "+trigger": "value.attr.r",
                }
            }
        },
    )
