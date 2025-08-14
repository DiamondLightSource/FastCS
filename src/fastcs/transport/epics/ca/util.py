from dataclasses import asdict

from softioc import builder

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, Waveform
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


EPICS_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String, Waveform)

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
    """Converts attributes on the `Attribute` to the
    field name/value in the record metadata."""
    return {"DESC": attribute.description}


def record_metadata_from_datatype(
    datatype: DataType[T], out_record: bool = False
) -> dict[str, str]:
    """Converts attributes on the `DataType` to the
    field name/value in the record metadata."""

    arguments = {
        DATATYPE_FIELD_TO_RECORD_FIELD[field]: value
        for field, value in asdict(datatype).items()
        if field in DATATYPE_FIELD_TO_RECORD_FIELD
    }

    if not out_record:
        # in type records don't have DRVL/DRVH fields
        arguments.pop("DRVL", None)
        arguments.pop("DRVH", None)

    match datatype:
        case Waveform():
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
                        datatype.names,
                        strict=False,
                    )
                )
                arguments.update(state_keys)
            elif out_record:  # no validators for in type records

                def _verify_in_datatype(_, value):
                    return value in datatype.names

                arguments["validate"] = _verify_in_datatype

    return arguments


def cast_from_epics_type(datatype: DataType[T], value: object) -> T:
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
                return datatype.validate(datatype.members[value])
            else:  # enum backed by string record
                return datatype.validate(datatype.enum_cls[value])
        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):
            return datatype.validate(value)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")


def cast_to_epics_type(datatype: DataType[T], value: T) -> object:
    """Casts from an attribute's datatype to an EPICS datatype."""
    match datatype:
        case Enum():
            if len(datatype.members) <= MBB_MAX_CHOICES:
                return datatype.index_of(datatype.validate(value))
            else:  # enum backed by string record
                return datatype.validate(value).name
        case datatype if issubclass(type(datatype), EPICS_ALLOWED_DATATYPES):
            return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")


def builder_callable_from_attribute(
    attribute: AttrR | AttrW | AttrRW, make_in_record: bool
):
    """Returns a callable to make the softioc record from an attribute instance."""
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
                return builder.longStringIn if make_in_record else builder.longStringOut
            else:
                return builder.mbbIn if make_in_record else builder.mbbOut
        case Waveform():
            return builder.WaveformIn if make_in_record else builder.WaveformOut
        case _:
            raise FastCSException(
                f"EPICS unsupported datatype on {attribute}: {attribute.datatype}"
            )
