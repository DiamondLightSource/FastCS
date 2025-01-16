from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from tango import AttrDataFormat

from fastcs.attributes import Attribute
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, WaveForm

TANGO_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String, WaveForm)

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
    arguments = {}
    arguments["doc"] = attribute.description if attribute.description else ""
    return arguments


def get_server_metadata_from_datatype(datatype: DataType[T]) -> dict[str, str]:
    arguments = {
        DATATYPE_FIELD_TO_SERVER_FIELD[field]: value
        for field, value in asdict(datatype).items()
        if field in DATATYPE_FIELD_TO_SERVER_FIELD
    }

    dtype = datatype.dtype

    match datatype:
        case WaveForm():
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


def get_cast_method_to_tango_type(datatype: DataType[T]) -> Callable[[T], object]:
    match datatype:
        case Enum():

            def cast_to_tango_type(value) -> int:
                return datatype.index_of(datatype.validate(value))
        case datatype if issubclass(type(datatype), TANGO_ALLOWED_DATATYPES):

            def cast_to_tango_type(value) -> object:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_to_tango_type


def get_cast_method_from_tango_type(datatype: DataType[T]) -> Callable[[object], T]:
    match datatype:
        case Enum():

            def cast_from_tango_type(value: object) -> T:
                return datatype.validate(datatype.members[value])

        case datatype if issubclass(type(datatype), TANGO_ALLOWED_DATATYPES):

            def cast_from_tango_type(value) -> T:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")

    return cast_from_tango_type
