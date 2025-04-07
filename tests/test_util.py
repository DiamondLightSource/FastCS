import pytest
from pvi.device import SignalR
from pydantic import ValidationError

from fastcs.util import snake_to_pascal


def test_snake_to_pascal():
    name1 = "name_in_snake_case"
    name2 = "name-not-in-snake-case"
    name3 = "name_with-different_separators"
    name4 = "name_with_numbers_1_2_3"
    name5 = "numbers_1_2_3_in_the_middle"
    name6 = "1_2_3_starting_with_numbers"
    name7 = "Name_With_%_Invalid_&_Symbols_£_"
    name8 = "name_in_lower_case"
    name9 = "NameAlreadyInPascalCase"
    assert snake_to_pascal(name1) == "NameInSnakeCase"
    assert snake_to_pascal(name2) == "name-not-in-snake-case"
    assert snake_to_pascal(name3) == "name_with-different_separators"
    assert snake_to_pascal(name4) == "NameWithNumbers123"
    assert snake_to_pascal(name5) == "Numbers123InTheMiddle"
    assert snake_to_pascal(name6) == "1_2_3_starting_with_numbers"
    assert snake_to_pascal(name7) == "Name_With_%_Invalid_&_Symbols_£_"
    assert snake_to_pascal(name8) == "NameInLowerCase"
    assert snake_to_pascal(name9) == "NameAlreadyInPascalCase"


def test_pvi_validation_error():
    name = snake_to_pascal("Name-With_%_Invalid-&-Symbols_£_")
    with pytest.raises(ValidationError):
        SignalR(name=name, read_pv="test")
