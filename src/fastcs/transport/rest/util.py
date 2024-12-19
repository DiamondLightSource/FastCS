from collections.abc import Callable

import numpy as np

from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, WaveForm

REST_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String)


def convert_datatype(datatype: DataType[T]) -> type:
    match datatype:
        case WaveForm():
            return list
        case _:
            return datatype.dtype


def get_cast_method_to_rest_type(datatype: DataType[T]) -> Callable[[T], object]:
    match datatype:
        case WaveForm():

            def cast_to_rest_type(value) -> list:
                return value.tolist()
        case datatype if issubclass(type(datatype), REST_ALLOWED_DATATYPES):

            def cast_to_rest_type(value):
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")

    return cast_to_rest_type


def get_cast_method_from_rest_type(datatype: DataType[T]) -> Callable[[object], T]:
    match datatype:
        case WaveForm():

            def cast_from_rest_type(value) -> T:
                return datatype.validate(np.array(value, dtype=datatype.array_dtype))
        case datatype if issubclass(type(datatype), REST_ALLOWED_DATATYPES):

            def cast_from_rest_type(value) -> T:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")

    return cast_from_rest_type
