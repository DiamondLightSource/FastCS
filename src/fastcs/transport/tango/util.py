from dataclasses import asdict
from typing import Any

from tango import AttrDataFormat

from fastcs.attributes import Attribute
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, Waveform

TANGO_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String, Waveform)

DATATYPE_FIELD_TO_SERVER_FIELD = {
    "units": "unit",
    "min": "min_value",
    "max": "max_value",
    "min_alarm": "min_alarm",
    "max_alarm": "min_alarm",
}


def get_server_metadata_from_attribute(
    attribute: Attribute[T],
) -> dict[str, Any]:
    """Gets the metadata for a Tango field from an attribute."""
    arguments = {}
    arguments["doc"] = attribute.description if attribute.description else ""
    return arguments


def get_server_metadata_from_datatype(datatype: DataType[T]) -> dict[str, str]:
    """Gets the metadata for a Tango field from a FastCS datatype."""
    arguments = {
        DATATYPE_FIELD_TO_SERVER_FIELD[field]: value
        for field, value in asdict(datatype).items()
        if field in DATATYPE_FIELD_TO_SERVER_FIELD
    }

    dtype = datatype.dtype

    match datatype:
        case Waveform():
            dtype = datatype.array_dtype
            match len(datatype.shape):
                case 1:
                    arguments["max_dim_x"] = datatype.shape[0]
                    arguments["dformat"] = AttrDataFormat.SPECTRUM
                case 2:
                    arguments["max_dim_x"], arguments["max_dim_y"] = datatype.shape
                    arguments["dformat"] = AttrDataFormat.IMAGE
                case _:
                    raise TypeError(
                        f"Unsupported shape {datatype.shape}, Tango supports up "
                        "to 2D arrays"
                    )
        case Float():
            arguments["format"] = f"%.{datatype.prec}"

    arguments["dtype"] = dtype
    for argument, value in arguments.items():
        if value is None:
            arguments[argument] = ""

    return arguments


def cast_to_tango_type(datatype: DataType[T], value: T) -> object:
    """Casts a value from FastCS to tango datatype."""
    match datatype:
        case Enum():
            return datatype.index_of(datatype.validate(value))
        case datatype if issubclass(type(datatype), TANGO_ALLOWED_DATATYPES):
            return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")


def cast_from_tango_type(datatype: DataType[T], value: object) -> T:
    """Casts a value from tango to FastCS datatype."""
    match datatype:
        case Enum():
            return datatype.validate(datatype.members[value])
        case datatype if issubclass(type(datatype), TANGO_ALLOWED_DATATYPES):
            return datatype.validate(value)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
