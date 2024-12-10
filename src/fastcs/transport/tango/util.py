from collections.abc import Callable

from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T

TANGO_ALLOWED_DATATYPES = (Bool, DataType, Enum, Float, Int, String)


def get_cast_method_to_tango_type(datatype: DataType[T]) -> Callable[[T], object]:
    match datatype:
        case Enum():

            def cast_to_tango_type(value) -> int:
                return datatype.validate(value).value
        case datatype if issubclass(type(datatype), TANGO_ALLOWED_DATATYPES):

            def cast_to_tango_type(value) -> object:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")
    return cast_to_tango_type


def get_cast_method_from_tango_type(datatype: DataType[T]) -> Callable[[object], T]:
    match datatype:
        case Enum(enum_cls):

            def cast_from_tango_type(value: object) -> T:
                return datatype.validate(enum_cls(value))

        case datatype if issubclass(type(datatype), TANGO_ALLOWED_DATATYPES):

            def cast_from_tango_type(value) -> T:
                return datatype.validate(value)
        case _:
            raise ValueError(f"Unsupported datatype {datatype}")

    return cast_from_tango_type
