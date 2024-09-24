import pytest

from fastcs.attributes import AttrR
from fastcs.backends.epics.util import (
    attr_is_enum,
    enum_index_to_value,
    enum_value_to_index,
)
from fastcs.datatypes import String


def test_attr_is_enum():
    assert not attr_is_enum(AttrR(String()))
    assert attr_is_enum(AttrR(String(), allowed_values=["disabled", "enabled"]))


def test_enum_index_to_value():
    """Test enum_index_to_value."""
    attribute = AttrR(String(), allowed_values=["disabled", "enabled"])

    assert enum_index_to_value(attribute, 0) == "disabled"
    assert enum_index_to_value(attribute, 1) == "enabled"
    with pytest.raises(IndexError, match="Invalid index"):
        enum_index_to_value(attribute, 2)

    with pytest.raises(ValueError, match="Cannot lookup value by index"):
        enum_index_to_value(AttrR(String()), 0)


def test_enum_value_to_index():
    attribute = AttrR(String(), allowed_values=["disabled", "enabled"])

    assert enum_value_to_index(attribute, "disabled") == 0
    assert enum_value_to_index(attribute, "enabled") == 1
    with pytest.raises(ValueError, match="not in allowed values"):
        enum_value_to_index(attribute, "off")

    with pytest.raises(ValueError, match="Cannot convert value to index"):
        enum_value_to_index(AttrR(String()), "disabled")
