import enum
from typing import Any

from fastcs.datatypes import Bool, DType_T, Enum, Float, Int, String, Waveform
from fastcs.datatypes.datatype import DataType

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


EPICS_ALLOWED_DATATYPES = (Bool, Enum, Float, Int, String, Waveform)
DEFAULT_STRING_WAVEFORM_LENGTH = 256

DATATYPE_FIELD_TO_IN_RECORD_FIELD = {
    "prec": "PREC",
    "units": "EGU",
    "min_alarm": "LOPR",
    "max_alarm": "HOPR",
}

DATATYPE_FIELD_TO_OUT_RECORD_FIELD = {
    "prec": "PREC",
    "units": "EGU",
    "min": "DRVL",
    "max": "DRVH",
    "min_alarm": "LOPR",
    "max_alarm": "HOPR",
}


def create_state_keys(datatype: Enum):
    """Creates a dictionary of state field keys to names"""
    return dict(
        zip(
            MBB_STATE_FIELDS,
            datatype.names,
            strict=False,
        )
    )


def cast_from_epics_type(datatype: DataType[DType_T], value: object) -> DType_T:
    """Casts from an EPICS datatype to a FastCS datatype."""
    match datatype:
        case Bool():
            if value == 0:
                return False
            elif value == 1:
                return True
            else:
                raise ValueError(f"Invalid bool value from EPICS record {value}")
        case Enum():
            if len(datatype.members) <= MBB_MAX_CHOICES:
                assert isinstance(value, int), "Got non-integer value for Enum"
                return datatype.validate(datatype.members[value])
            else:  # enum backed by string record
                assert isinstance(value, str), "Got non-string value for long Enum"
                # python typing can't narrow the nested generic enum_cls
                assert issubclass(datatype.enum_cls, enum.Enum), "Invalid Enum.enum_cls"
                enum_member = datatype.enum_cls[value]
                return datatype.validate(enum_member)
        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):
            return datatype.validate(value)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")


def cast_to_epics_type(datatype: DataType[DType_T], value: DType_T) -> Any:
    """Casts from an attribute's datatype to an EPICS datatype."""
    match datatype:
        case Enum():
            if len(datatype.members) <= MBB_MAX_CHOICES:
                return datatype.index_of(datatype.validate(value))
            else:  # enum backed by string record
                return datatype.validate(value).name
        case String() as string:
            if string.length is not None:
                return value[: string.length]
            else:
                return value[:DEFAULT_STRING_WAVEFORM_LENGTH]
        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):
            return value
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
