import pytest
from pvi.device import SignalR
from pydantic import ValidationError

from fastcs.util import snake_to_pascal


def test_snake_to_pascal():
    name1 = "a-b-c-d-e"
    name2 = "a_b_c_d_e"
    name3 = "name_with-different_separators"
    name4 = "1_2_3-a-b-c"
    name5 = "NameAlreadyInPascalCase"
    name6 = "Name-With_%_Invalid-&-Symbols_£_"
    name7 = "123A_b-C-d-e_"
    assert snake_to_pascal(name1) == "ABCDE"
    assert snake_to_pascal(name2) == "ABCDE"
    assert snake_to_pascal(name3) == "NameWithDifferentSeparators"
    assert snake_to_pascal(name4) == "123ABC"
    assert snake_to_pascal(name5) == "NameAlreadyInPascalCase"
    assert snake_to_pascal(name6) == "NameWith%Invalid&Symbols£"
    assert snake_to_pascal(name7) == "123ABCDE"


def test_pvi__validation_error():
    name = snake_to_pascal("Name-With_%_Invalid-&-Symbols_£_")
    with pytest.raises(ValidationError):
        SignalR(name=name, read_pv="test")
