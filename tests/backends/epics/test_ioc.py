from pytest_mock import MockerFixture

from fastcs.backends.epics.ioc import EpicsIOC
from fastcs.mapping import Mapping


def test_ioc(mocker: MockerFixture, mapping: Mapping):
    builder_mock = mocker.patch("fastcs.backends.epics.ioc.builder")

    EpicsIOC("DEVICE", mapping)

    builder_mock.aIn.assert_called_once_with("ReadWriteFloat_RBV", PREC=2)
    builder_mock.aOut.assert_any_call(
        "ReadWriteFloat", always_update=True, on_update=mocker.ANY, PREC=2
    )
    builder_mock.boolIn.assert_called_once_with("ReadBool", ZNAM="OFF", ONAM="ON")
    builder_mock.boolOut.assert_called_once_with(
        "WriteBool", ZNAM="OFF", ONAM="ON", always_update=True, on_update=mocker.ANY
    )
    builder_mock.longIn.assert_any_call("ReadInt")
    builder_mock.longIn.assert_any_call("ReadWriteInt_RBV")
    builder_mock.longOut.assert_called_with(
        "ReadWriteInt", always_update=True, on_update=mocker.ANY
    )
    builder_mock.longStringIn.assert_called_once_with("StringEnum_RBV")
    builder_mock.longStringOut.assert_called_once_with(
        "StringEnum", always_update=True, on_update=mocker.ANY
    )
    builder_mock.aOut.assert_any_call(
        "Go", initial_value=0, always_update=True, on_update=mocker.ANY
    )
