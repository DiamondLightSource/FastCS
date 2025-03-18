import numpy as np

from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, Waveform

REST_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String)


def convert_datatype(datatype: DataType[T]) -> type:
    """Converts a datatype to a rest serialisable type."""
    match datatype:
        case Waveform():
            return list
        case _:
            return datatype.dtype


def cast_to_rest_type(datatype: DataType[T], value: T) -> object:
    """Casts from an attribute value to a rest value."""
    match datatype:
        case Waveform():
            return value.tolist()
        case datatype if issubclass(type(datatype), REST_ALLOWED_DATATYPES):
            return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")


def cast_from_rest_type(datatype: DataType[T], value: object) -> T:
    """Casts from a rest value to an attribute datatype."""
    match datatype:
        case Waveform():
            return datatype.validate(np.array(value, dtype=datatype.array_dtype))
        case datatype if issubclass(type(datatype), REST_ALLOWED_DATATYPES):
            return datatype.validate(value)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
