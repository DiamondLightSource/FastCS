import enum

import pytest
from softioc import builder

from fastcs.attributes import AttrRW
from fastcs.datatypes import Bool, Enum, Float, Int, String
from fastcs.transport.epics.ca.util import (
    builder_callable_from_attribute,
    cast_from_epics_type,
    cast_to_epics_type,
)


class ShortEnum(enum.Enum):
    NOT = 0
    TOO = 1
    MANY = 2
    VALUES = 3


class LongEnum(enum.Enum):
    THIS = 0
    IS = 1
    AN = 2
    ENUM = 3
    WITH = 4
    ALTOGETHER = 5
    TOO = 6
    MANY = 7
    VALUES = 8
    TO = 9
    BE = 10
    DESCRIBED = 11
    BY = 12
    MBB = 14
    TYPE = 15
    EPICS = 16
    RECORDS = 17


class LongMixedEnum(enum.Enum):
    THIS = "the value is THIS"
    IS = 1
    AN = "the value is AN"
    ENUM = 3
    WITH = "the value is WITH"
    ALTOGETHER = 5
    TOO = "the value is TOO"
    MANY = 7
    VALUES = "the value is VALUES"
    TO = 9
    BE = "the value is BE"
    DESCRIBED = 11
    BY = "the value is BY"
    MBB = 13
    TYPE = "the value is TYPE"
    EPICS = None
    RECORDS = "the value is RECORDS"


class ShortMixedEnum(enum.Enum):
    STRING_MEMBER = "I am a string"
    INT_MEMBER = 2
    NONE_MEMBER = None


@pytest.mark.parametrize(
    "datatype,input,output",
    [
        (Enum(ShortEnum), ShortEnum.TOO, 1),
        # in CA, enums with too many values become epics strings
        (Enum(LongMixedEnum), LongMixedEnum.BE, "BE"),  # string value
        (Enum(LongMixedEnum), LongMixedEnum.EPICS, "EPICS"),  # None value
        (Enum(LongMixedEnum), LongMixedEnum.MBB, "MBB"),  # int value
        (Int(), 4, 4),
        (Float(), 1.0, 1.0),
        (Bool(), True, True),
        (String(), "hey", "hey"),
        # shorter enums can be represented by integers from 0-15
        (Enum(ShortMixedEnum), ShortMixedEnum.STRING_MEMBER, 0),
        (Enum(ShortMixedEnum), ShortMixedEnum.INT_MEMBER, 1),
        (Enum(ShortMixedEnum), ShortMixedEnum.NONE_MEMBER, 2),
    ],
)
def test_casting_to_epics(datatype, input, output):
    assert cast_to_epics_type(datatype, input) == output


@pytest.mark.parametrize(
    "datatype, input",
    [
        (object(), 0),
        # TODO cover Waveform and Table cases
        (Enum(ShortEnum), 0),  # can't use index
        (Enum(ShortEnum), LongEnum.TOO),  # wrong enum.Enum class
        (Int(), 4.0),
        (Float(), 1),
        (Bool(), None),
        (String(), 10),
    ],
)
def test_cast_to_epics_validations(datatype, input):
    with pytest.raises(ValueError):
        cast_to_epics_type(datatype, input)


@pytest.mark.parametrize(
    "datatype,from_epics,result",
    [
        # long enums backed by strings
        (Enum(LongMixedEnum), "BE", LongMixedEnum.BE),  # string value
        (Enum(LongMixedEnum), "EPICS", LongMixedEnum.EPICS),  # None value
        (Enum(LongMixedEnum), "MBB", LongMixedEnum.MBB),  # int value
        (Int(), 4, 4),
        (Float(), 1.0, 1.0),
        (Bool(), True, True),
        (String(), "hey", "hey"),
        (Enum(ShortEnum), 2, ShortEnum.MANY),
        # short enums backed by mbbi/mbbo
        (Enum(ShortMixedEnum), 0, ShortMixedEnum.STRING_MEMBER),
        (Enum(ShortMixedEnum), 1, ShortMixedEnum.INT_MEMBER),
        (Enum(ShortMixedEnum), 2, ShortMixedEnum.NONE_MEMBER),
        (Bool(), 1, True),
        (Bool(), 0, False),
    ],
)
def test_cast_from_epics_type(datatype, from_epics, result):
    assert cast_from_epics_type(datatype, from_epics) == result


@pytest.mark.parametrize(
    "datatype, input",
    [
        (object(), 0),
        (Bool(), 3),
    ],
)
def test_cast_from_epics_validations(datatype, input):
    with pytest.raises(ValueError):
        cast_from_epics_type(datatype, input)


@pytest.mark.parametrize(
    "datatype,in_record,out_record",
    [
        (Enum(ShortEnum), builder.mbbIn, builder.mbbOut),
        # long enums use string even if all values are ints
        (Enum(LongEnum), builder.longStringIn, builder.longStringOut),
        (Enum(LongMixedEnum), builder.longStringIn, builder.longStringOut),
    ],
)
def test_builder_callable_enum_types(datatype, in_record, out_record):
    attr = AttrRW(datatype)
    assert builder_callable_from_attribute(attr, False) == out_record
    assert builder_callable_from_attribute(attr, True) == in_record
