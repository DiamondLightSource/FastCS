import asyncio
import enum

import numpy as np
import pytest
from pvi.device import SignalR
from pydantic import ValidationError

from fastcs.attributes import AttrR, AttrRW
from fastcs.backend import Backend
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String
from fastcs.util import numpy_to_fastcs_datatype, snake_to_pascal


def test_snake_to_pascal():
    name1 = "name_in_snake_case"
    name2 = "name-not-in-snake-case"
    name3 = "name_with-different_separators"
    name4 = "name_with_numbers_1_2_3"
    name5 = "numbers_1_2_3_in_the_middle"
    name6 = "1_2_3_starting_with_numbers"
    name7 = "name1_with2_a3_number4"
    name8 = "name_in_lower_case"
    name9 = "NameAlreadyInPascalCase"
    name10 = "Name_With_%_Invalid_&_Symbols_£_"
    name11 = "a_b_c_d"
    name12 = "test"
    assert snake_to_pascal(name1) == "NameInSnakeCase"
    assert snake_to_pascal(name2) == "name-not-in-snake-case"
    assert snake_to_pascal(name3) == "name_with-different_separators"
    assert snake_to_pascal(name4) == "NameWithNumbers123"
    assert snake_to_pascal(name5) == "Numbers123InTheMiddle"
    assert snake_to_pascal(name6) == "1_2_3_starting_with_numbers"
    assert snake_to_pascal(name7) == "Name1With2A3Number4"
    assert snake_to_pascal(name8) == "NameInLowerCase"
    assert snake_to_pascal(name9) == "NameAlreadyInPascalCase"
    assert snake_to_pascal(name10) == "Name_With_%_Invalid_&_Symbols_£_"
    assert snake_to_pascal(name11) == "ABCD"
    assert snake_to_pascal(name12) == "Test"


def test_pvi_validation_error():
    name = snake_to_pascal("Name-With_%_Invalid-&-Symbols_£_")
    with pytest.raises(ValidationError):
        SignalR(name=name, read_pv="test")


@pytest.mark.parametrize(
    "numpy_type, fastcs_datatype",
    [
        (np.float16, Float()),
        (np.float32, Float()),
        (np.int16, Int()),
        (np.int32, Int()),
        (np.bool, Bool()),
        (np.dtype("S1000"), String()),
        (np.dtype("U25"), String()),
        (np.dtype(">i4"), Int()),
        (np.dtype("d"), Float()),
    ],
)
def test_numpy_to_fastcs_datatype(numpy_type, fastcs_datatype):
    assert fastcs_datatype == numpy_to_fastcs_datatype(numpy_type)


def test_hinted_attributes_verified():
    loop = asyncio.get_event_loop()

    class ControllerWithWrongType(Controller):
        hinted_wrong_type: AttrR[int]

        async def initialise(self):
            self.hinted_wrong_type = AttrR(Float())  # type: ignore
            self.attributes["hinted_wrong_type"] = self.hinted_wrong_type

    with pytest.raises(RuntimeError) as excinfo:
        Backend(ControllerWithWrongType(), loop)
    assert str(excinfo.value) == (
        "Controller 'ControllerWithWrongType' introspection of hinted attribute "
        "'hinted_wrong_type' does not match defined datatype. "
        "Expected 'int', got 'float'."
    )

    class ControllerWithMissingAttr(Controller):
        hinted_int_missing: AttrR[int]

    with pytest.raises(RuntimeError) as excinfo:
        Backend(ControllerWithMissingAttr(), loop)
    assert str(excinfo.value) == (
        "Controller `ControllerWithMissingAttr` failed to introspect hinted attribute "
        "`hinted_int_missing` during initialisation"
    )

    class ControllerAttrWrongAccessMode(Controller):
        hinted: AttrR[int]

        async def initialise(self):
            self.hinted = AttrRW(Int())
            self.attributes["hinted"] = self.hinted

    with pytest.raises(RuntimeError) as excinfo:
        Backend(ControllerAttrWrongAccessMode(), loop)
    assert str(excinfo.value) == (
        "Controller 'ControllerAttrWrongAccessMode' introspection of hinted attribute "
        "'hinted' does not match defined access mode. Expected 'AttrR', got 'AttrRW'."
    )

    class MyEnum(enum.Enum):
        A = 0
        B = 1

    class MyEnum2(enum.Enum):
        A = 2
        B = 3

    class ControllerWrongEnumClass(Controller):
        hinted_enum: AttrRW[MyEnum] = AttrRW(Enum(MyEnum2))

    with pytest.raises(RuntimeError) as excinfo:
        Backend(ControllerWrongEnumClass(), loop)
    assert str(excinfo.value) == (
        "Controller 'ControllerWrongEnumClass' introspection of hinted attribute "
        "'hinted_enum' does not match defined datatype. "
        "Expected 'MyEnum', got 'MyEnum2'."
    )
