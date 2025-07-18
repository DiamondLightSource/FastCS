import numpy as np
import pytest
from pvi.device import SignalR
from pydantic import ValidationError

from fastcs.datatypes import Bool, Float, Int, String
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
