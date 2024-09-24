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


def attr_is_enum(attribute: Attribute) -> bool:
    """Check if the `Attribute` has a `String` datatype and has `allowed_values` set.

    Args:
        attribute: The `Attribute` to check

    Returns:
        `True` if `Attribute` is an enum, else `False`

    """
    match attribute:
        case Attribute(
            datatype=String(), allowed_values=allowed_values
        ) if allowed_values is not None and len(allowed_values) <= MBB_MAX_CHOICES:
            return True
        case _:
            return False


def enum_value_to_index(attribute: Attribute[T], value: T) -> int:
    """Convert the given value to the index within the allowed_values of the Attribute

    Args:
        `attribute`: The attribute
        `value`: The value to convert

    Returns:
        The index of the `value`

    Raises:
        ValueError: If `attribute` has no allowed values or `value` is not a valid
            option

    """
    if attribute.allowed_values is None:
        raise ValueError(
            "Cannot convert value to index for Attribute without allowed values"
        )

    try:
        return attribute.allowed_values.index(value)
    except ValueError:
        raise ValueError(
            f"{value} not in allowed values of {attribute}: {attribute.allowed_values}"
        ) from None


def enum_index_to_value(attribute: Attribute[T], index: int) -> T:
    """Lookup the value from the allowed_values of an attribute at the given index.

    Parameters:
        attribute: The `Attribute` to lookup the index from
        index: The index of the value to retrieve

    Returns:
        The value at the specified index in the allowed values list.

    Raises:
        IndexError: If the index is out of bounds

    """
    if attribute.allowed_values is None:
        raise ValueError(
            "Cannot lookup value by index for Attribute without allowed values"
        )

    try:
        return attribute.allowed_values[index]
    except IndexError:
        raise IndexError(
            f"Invalid index {index} into allowed values: {attribute.allowed_values}"
        ) from None
