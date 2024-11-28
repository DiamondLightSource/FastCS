import pytest
from tango import DevState
from tango.test_context import DeviceTestContext

from fastcs.transport.tango.adapter import TangoTransport


class TestTangoDevice:
    @pytest.fixture(scope="class")
    def tango_context(self, assertable_controller):
        # https://tango-controls.readthedocs.io/projects/pytango/en/v9.5.1/testing/test_context.html
        device = TangoTransport(assertable_controller)._dsr._device
        with DeviceTestContext(device, debug=0) as proxy:
            yield proxy

    def test_list_attributes(self, tango_context):
        assert list(tango_context.get_attribute_list()) == [
            "BigEnum",
            "ReadBool",
            "ReadInt",
            "ReadWriteFloat",
            "ReadWriteInt",
            "StringEnum",
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

    def test_string_enum(self, assertable_controller, tango_context):
        expect = ""
        with assertable_controller.assert_read_here(["string_enum"]):
            result = tango_context.read_attribute("StringEnum").value
        assert result == expect
        new = "new"
        with assertable_controller.assert_write_here(["string_enum"]):
            tango_context.write_attribute("StringEnum", new)
        assert tango_context.read_attribute("StringEnum").value == new

    def test_big_enum(self, assertable_controller, tango_context):
        expect = 0
        with assertable_controller.assert_read_here(["big_enum"]):
            result = tango_context.read_attribute("BigEnum").value
        assert result == expect

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
