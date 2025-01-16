from collections.abc import Callable
from dataclasses import asdict

from softioc import builder

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, WaveForm
from fastcs.exceptions import FastCSException

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
}


def record_metadata_from_attribute(
    attribute: Attribute[T],
) -> dict[str, str | None]:
    return {"DESC": attribute.description}


def record_metadata_from_datatype(datatype: DataType[T]) -> dict[str, str]:
    arguments = {
        DATATYPE_FIELD_TO_RECORD_FIELD[field]: value
        for field, value in asdict(datatype).items()
        if field in DATATYPE_FIELD_TO_RECORD_FIELD
    }

    match datatype:
        case WaveForm():
            if len(datatype.shape) != 1:
                raise TypeError(
                    f"Unsupported shape {datatype.shape}, the EPICS backend only "
                    "supports to 1D arrays"
                )
            arguments["length"] = datatype.shape[0]
        case Enum():
            if len(datatype.members) <= MBB_MAX_CHOICES:
                state_keys = dict(
                    zip(
                        MBB_STATE_FIELDS,
                        [member.name for member in datatype.members],
                        strict=False,
                    )
                )
                arguments.update(state_keys)

    return arguments


def get_callable_from_epics_type(datatype: DataType[T]) -> Callable[[object], T]:
    match datatype:
        case Enum():

            def cast_from_epics_type(value: object) -> T:
                return datatype.validate(datatype.members[value])

        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):

            def cast_from_epics_type(value) -> T:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_from_epics_type


def get_callable_to_epics_type(datatype: DataType[T]) -> Callable[[T], object]:
    match datatype:
        case Enum():

            def cast_to_epics_type(value) -> object:
                return datatype.index_of(datatype.validate(value))
        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):

            def cast_to_epics_type(value) -> object:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_to_epics_type


def builder_callable_from_attribute(
    attribute: AttrR | AttrW | AttrRW, make_in_record: bool
):
    match attribute.datatype:
        case Bool():
            return builder.boolIn if make_in_record else builder.boolOut
        case Int():
            return builder.longIn if make_in_record else builder.longOut
        case Float():
            return builder.aIn if make_in_record else builder.aOut
        case String():
            return builder.longStringIn if make_in_record else builder.longStringOut
        case Enum():
            if len(attribute.datatype.members) > MBB_MAX_CHOICES:
                return builder.longIn if make_in_record else builder.longOut
            else:
                return builder.mbbIn if make_in_record else builder.mbbOut
        case WaveForm():
            return builder.WaveformIn if make_in_record else builder.WaveformOut
        case _:
            raise FastCSException(
                f"EPICS unsupported datatype on {attribute}: {attribute.datatype}"
            )
