from fastcs.attributes import Attribute
from fastcs.datatypes import String, T

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


def convert_if_enum(attribute: Attribute[T], value: T) -> T | int:
    """Check if `attribute` is a string enum and if so convert `value` to index of enum.

    Args:
        `attribute`: The attribute to be set
        `value`: The value

    Returns:
        The index of the `value` if the `attribute` is an enum, else `value`

    Raises:
        ValueError: If `attribute` is an enum and `value` is not in its allowed values

    """
    match attribute:
        case Attribute(
            datatype=String(), allowed_values=allowed_values
        ) if allowed_values is not None and len(allowed_values) <= MBB_MAX_CHOICES:
            if value in allowed_values:
                return allowed_values.index(value)
            else:
                raise ValueError(f"'{value}' not in allowed values {allowed_values}")
        case _:
            return value
