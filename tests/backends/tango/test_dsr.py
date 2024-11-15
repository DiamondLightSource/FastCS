import copy
import re
from typing import Any

import pytest
from tango import DevState
from tango.test_context import DeviceTestContext

from fastcs.attributes import AttrR
from fastcs.backends.tango.backend import TangoBackend
from fastcs.datatypes import Bool, Float, Int, String


def pascal_2_snake(input: list[str]) -> list[str]:
    """
    Converts the last entry in a list of strings
    """
    snake_list = copy.deepcopy(input)
    snake_list[-1] = re.sub(r"(?<!^)(?=[A-Z])", "_", snake_list[-1]).lower()
    return snake_list


class TestTangoDevice:
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self, assertable_controller):
        self.controller = assertable_controller

    @pytest.fixture(scope="class")
    def tango_context(self):
        # https://tango-controls.readthedocs.io/projects/pytango/en/v9.5.1/testing/test_context.html
        device = TangoBackend(self.controller)._dsr._device
        with DeviceTestContext(device) as proxy:
            yield proxy

    @pytest.fixture(scope="class")
    def client_read(self, tango_context):
        def _read_attribute(path: list[str], expected: Any):
            attribute = "_".join(path)
            with self.controller.assertPerformed(pascal_2_snake(path), "READ"):
                result = tango_context.read_attribute(attribute).value
            assert result == expected

        return _read_attribute

    @pytest.fixture(scope="class")
    def client_write(self, tango_context):
        def _write_attribute(path: list[str], expected: Any):
            attribute = "_".join(path)
            with self.controller.assertPerformed(pascal_2_snake(path), "WRITE"):
                tango_context.write_attribute(attribute, expected)

        return _write_attribute

    @pytest.fixture(scope="class")
    def client_exec(self, tango_context):
        def _exec_command(path: list[str]):
            command = "_".join(path)
            with self.controller.assertPerformed(pascal_2_snake(path), "EXECUTE"):
                tango_context.command_inout(command)

        return _exec_command

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
        expected = "The device is in ON state."
        assert tango_context.command_inout("Status") == expected

    def test_read_int(self, client_read):
        client_read(["ReadInt"], AttrR(Int())._value)

    def test_read_write_int(self, client_read, client_write):
        client_read(["ReadWriteInt"], AttrR(Int())._value)
        client_write(["ReadWriteInt"], AttrR(Int())._value)

    def test_read_write_float(self, client_read, client_write):
        client_read(["ReadWriteFloat"], AttrR(Float())._value)
        client_write(["ReadWriteFloat"], AttrR(Float())._value)

    def test_read_bool(self, client_read):
        client_read(["ReadBool"], AttrR(Bool())._value)

    def test_write_bool(self, client_write):
        client_write(["WriteBool"], AttrR(Bool())._value)

    def test_string_enum(self, client_read, client_write):
        enum = AttrR(String(), allowed_values=["red", "green", "blue"])._value
        client_read(["StringEnum"], enum)
        client_write(["StringEnum"], enum)

    def test_big_enum(self, client_read):
        client_read(["BigEnum"], AttrR(Int(), allowed_values=list(range(1, 18)))._value)

    def test_go(self, client_exec):
        client_exec(["Go"])

    def test_read_child1(self, client_read):
        client_read(["SubController01", "ReadInt"], AttrR(Int())._value)

    def test_read_child2(self, client_read):
        client_read(["SubController02", "ReadInt"], AttrR(Int())._value)
