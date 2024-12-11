from collections.abc import Callable
from dataclasses import asdict

from fastcs.attributes import Attribute
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, WaveForm

_MBB_FIELD_PREFIXES = (
    "ZR",
    "ON",
    "TW",
    "TH",
    "FR",
    "FV",
    "SX",
    "SV",
    "EI",
    "NI",
    "TE",
    "EL",
    "TV",
    "TT",
    "FT",
    "FF",
)

MBB_STATE_FIELDS = tuple(f"{p}ST" for p in _MBB_FIELD_PREFIXES)
MBB_VALUE_FIELDS = tuple(f"{p}VL" for p in _MBB_FIELD_PREFIXES)
MBB_MAX_CHOICES = len(_MBB_FIELD_PREFIXES)


EPICS_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String, WaveForm)

DATATYPE_FIELD_TO_RECORD_FIELD = {
    "prec": "PREC",
    "units": "EGU",
    "min": "DRVL",
    "max": "DRVH",
    "min_alarm": "LOPR",
    "max_alarm": "HOPR",
    "znam": "ZNAM",
    "onam": "ONAM",
    "shape": "length",
}


def get_record_metadata_from_attribute(
    attribute: Attribute[T],
) -> dict[str, str | None]:
    return {"DESC": attribute.description}


def get_record_metadata_from_datatype(datatype: DataType[T]) -> dict[str, str]:
    return {
        DATATYPE_FIELD_TO_RECORD_FIELD[field]: value
        for field, value in asdict(datatype).items()
        if field in DATATYPE_FIELD_TO_RECORD_FIELD
    }


def get_cast_method_to_epics_type(datatype: DataType[T]) -> Callable[[T], object]:
    match datatype:
        case Enum():

            def cast_to_epics_type(value) -> str | int:
                return datatype.validate(value).value
        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):

            def cast_to_epics_type(value) -> object:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_to_epics_type


def get_cast_method_from_epics_type(datatype: DataType[T]) -> Callable[[object], T]:
    match datatype:
        case Enum(enum_cls):

            def cast_from_epics_type(value: object) -> T:
                return datatype.validate(enum_cls(value))

        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):

            def cast_from_epics_type(value) -> T:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_from_epics_type
