import pytest

from fastcs.attributes import AttrR
from fastcs.backends.epics.util import convert_if_enum
from fastcs.datatypes import String


def test_convert_if_enum():
    string_attr = AttrR(String())
    enum_attr = AttrR(String(), allowed_values=["disabled", "enabled"])

    assert convert_if_enum(string_attr, "enabled") == "enabled"

    assert convert_if_enum(enum_attr, "enabled") == 1

    with pytest.raises(ValueError):
        convert_if_enum(enum_attr, "off")
