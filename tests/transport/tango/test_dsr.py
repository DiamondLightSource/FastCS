import enum

import numpy as np
import pytest
from pytest_mock import MockerFixture
from tango import DevState
from tango.test_context import DeviceTestContext
from tests.assertable_controller import (
    AssertableController,
    TestHandler,
    TestSender,
    TestUpdater,
)

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Enum, Float, Int, String, WaveForm
from fastcs.transport.tango.adapter import TangoTransport


class TangoAssertableController(AssertableController):
    read_int = AttrR(Int(), handler=TestUpdater())
    read_write_int = AttrRW(Int(), handler=TestHandler())
    read_write_float = AttrRW(Float())
    read_bool = AttrR(Bool())
    write_bool = AttrW(Bool(), handler=TestSender())
    read_string = AttrRW(String())
    enum = AttrRW(Enum(enum.IntEnum("Enum", {"RED": 0, "GREEN": 1, "BLUE": 2})))
    one_d_waveform = AttrRW(WaveForm(np.int32, (10,)))
    two_d_waveform = AttrRW(WaveForm(np.int32, (10, 10)))
    big_enum = AttrR(
        Int(
            allowed_values=list(range(17)),
        ),
    )


@pytest.fixture(scope="class")
def assertable_controller(class_mocker: MockerFixture):
    return TangoAssertableController(class_mocker)


class TestTangoContext:
    @pytest.fixture(scope="class")
    def tango_context(self, assertable_controller):
        # https://tango-controls.readthedocs.io/projects/pytango/en/v9.5.1/testing/test_context.html
        device = TangoTransport(assertable_controller)._dsr._device
        with DeviceTestContext(device, debug=0) as proxy:
            yield proxy

    def test_list_attributes(self, tango_context):
        assert list(tango_context.get_attribute_list()) == [
            "BigEnum",
            "Enum",
            "OneDWaveform",
            "ReadBool",
            "ReadInt",
            "ReadString",
            "ReadWriteFloat",
            "ReadWriteInt",
            "TwoDWaveform",
            "WriteBool",
            "SubController01_ReadInt",
            "SubController02_ReadInt",
            "State",
            "Status",
        ]

    def test_list_commands(self, tango_context):
        assert list(tango_context.get_command_list()) == [
            "Go",
            "Init",
            "State",
            "Status",
        ]

    def test_state(self, tango_context):
        assert tango_context.command_inout("State") == DevState.ON

    def test_status(self, tango_context):
        expect = "The device is in ON state."
        assert tango_context.command_inout("Status") == expect

    def test_read_int(self, assertable_controller, tango_context):
        expect = 0
        with assertable_controller.assert_read_here(["read_int"]):
            result = tango_context.read_attribute("ReadInt").value
        assert result == expect

    def test_read_write_int(self, assertable_controller, tango_context):
        expect = 0
        with assertable_controller.assert_read_here(["read_write_int"]):
            result = tango_context.read_attribute("ReadWriteInt").value
        assert result == expect
        new = 9
        with assertable_controller.assert_write_here(["read_write_int"]):
            tango_context.write_attribute("ReadWriteInt", new)
        assert tango_context.read_attribute("ReadWriteInt").value == new

    def test_read_write_float(self, assertable_controller, tango_context):
        expect = 0.0
        with assertable_controller.assert_read_here(["read_write_float"]):
            result = tango_context.read_attribute("ReadWriteFloat").value
        assert result == expect
        new = 0.5
        with assertable_controller.assert_write_here(["read_write_float"]):
            tango_context.write_attribute("ReadWriteFloat", new)
        assert tango_context.read_attribute("ReadWriteFloat").value == new

    def test_read_bool(self, assertable_controller, tango_context):
        expect = False
        with assertable_controller.assert_read_here(["read_bool"]):
            result = tango_context.read_attribute("ReadBool").value
        assert result == expect

    def test_write_bool(self, assertable_controller, tango_context):
        with assertable_controller.assert_write_here(["write_bool"]):
            tango_context.write_attribute("WriteBool", True)

    def test_enum(self, assertable_controller, tango_context):
        enum_attr = assertable_controller.attributes["enum"]
        enum_cls = enum_attr.datatype.dtype
        assert isinstance(enum_attr.get(), enum_cls)
        assert enum_attr.get() == enum_cls(0)
        expect = 0
        with assertable_controller.assert_read_here(["enum"]):
            result = tango_context.read_attribute("Enum").value
        assert result == expect
        new = 1
        with assertable_controller.assert_write_here(["enum"]):
            tango_context.write_attribute("Enum", new)
        assert tango_context.read_attribute("Enum").value == new
        assert isinstance(enum_attr.get(), enum_cls)
        assert enum_attr.get() == enum_cls(1)

    def test_big_enum(self, assertable_controller, tango_context):
        expect = 0
        with assertable_controller.assert_read_here(["big_enum"]):
            result = tango_context.read_attribute("BigEnum").value
        assert result == expect

    def test_1d_waveform(self, assertable_controller, tango_context):
        expect = np.zeros((10,), dtype=np.int32)
        with assertable_controller.assert_read_here(["one_d_waveform"]):
            result = tango_context.read_attribute("OneDWaveform").value
        assert np.array_equal(result, expect)
        new = np.array([1, 2, 3], dtype=np.int32)
        with assertable_controller.assert_write_here(["one_d_waveform"]):
            tango_context.write_attribute("OneDWaveform", new)
        assert np.array_equal(tango_context.read_attribute("OneDWaveform").value, new)

    def test_2d_waveform(self, assertable_controller, tango_context):
        expect = np.zeros((10, 10), dtype=np.int32)
        with assertable_controller.assert_read_here(["two_d_waveform"]):
            result = tango_context.read_attribute("TwoDWaveform").value
        assert np.array_equal(result, expect)
        new = np.array([[1, 2, 3]], dtype=np.int32)
        with assertable_controller.assert_write_here(["two_d_waveform"]):
            tango_context.write_attribute("TwoDWaveform", new)
        assert np.array_equal(tango_context.read_attribute("TwoDWaveform").value, new)

    def test_go(self, assertable_controller, tango_context):
        with assertable_controller.assert_execute_here(["go"]):
            tango_context.command_inout("Go")

    def test_read_child1(self, assertable_controller, tango_context):
        expect = 0
        with assertable_controller.assert_read_here(["SubController01", "read_int"]):
            result = tango_context.read_attribute("SubController01_ReadInt").value
        assert result == expect

    def test_read_child2(self, assertable_controller, tango_context):
        expect = 0
        with assertable_controller.assert_read_here(["SubController02", "read_int"]):
            result = tango_context.read_attribute("SubController02_ReadInt").value
        assert result == expect