import math
import time
from dataclasses import asdict

import numpy as np
from numpy.typing import DTypeLike
from p4p.nt import NTEnum, NTNDArray, NTScalar, NTTable

from fastcs.attributes import Attribute
from fastcs.datatypes import Bool, Enum, Float, Int, String, T, Table, Waveform

P4P_ALLOWED_DATATYPES = (Int, Float, String, Bool, Enum, Waveform, Table)


_P4P_EXTRA = [("description", ("u", None, [("defval", "s")]))]
_P4P_BOOL = NTScalar("?", extra=_P4P_EXTRA)
_P4P_STRING = NTScalar("s", extra=_P4P_EXTRA)


_P4P_EXTRA_NUMERICAL = [
    ("units", ("u", None, [("defval", "s")])),
    ("min", ("u", None, [("defval", "d")])),
    ("max", ("u", None, [("defval", "d")])),
    ("min_alarm", ("u", None, [("defval", "d")])),
    ("max_alarm", ("u", None, [("defval", "d")])),
]
_P4P_INT = NTScalar("i", extra=_P4P_EXTRA + _P4P_EXTRA_NUMERICAL)

_P4P_EXTRA_FLOAT = [("prec", ("u", None, [("defval", "i")]))]
_P4P_FLOAT = NTScalar("d", extra=_P4P_EXTRA + _P4P_EXTRA_NUMERICAL + _P4P_EXTRA_FLOAT)


# https://epics-base.github.io/pvxs/nt.html#alarm-t
RECORD_ALARM_STATUS = 3
NO_ALARM_STATUS = 0
MAJOR_ALARM_SEVERITY = 2
NO_ALARM_SEVERITY = 0

# https://numpy.org/devdocs/reference/arrays.dtypes.html#arrays-dtypes
# Some numpy dtypes don't match directly with the p4p ones
_NUMPY_DTYPE_TO_P4P_DTYPE = {
    "S": "s",  # Raw bytes to unicode bytes
    "U": "s",
}


def _table_with_numpy_dtypes_to_p4p_dtypes(numpy_dtypes: list[tuple[str, DTypeLike]]):
    p4p_dtypes = []
    for name, numpy_dtype in numpy_dtypes:
        dtype_char = np.dtype(numpy_dtype).char
        dtype_char = _NUMPY_DTYPE_TO_P4P_DTYPE.get(dtype_char, dtype_char)
        if dtype_char in ("e", "h", "H"):
            raise ValueError(
                "Table has a 16 bit numpy datatype. "
                "Not supported in p4p, use 32 or 64 instead."
            )
        p4p_dtypes.append((name, dtype_char))
    return p4p_dtypes


def get_p4p_type(
    attribute: Attribute,
) -> NTScalar | NTEnum | NTNDArray | NTTable:
    match attribute.datatype:
        case Int():
            return _P4P_INT
        case Float():
            return _P4P_FLOAT
        case String():
            return _P4P_STRING
        case Bool():
            return _P4P_BOOL
        case Enum():
            return NTEnum()
        case Waveform():
            # TODO: https://github.com/DiamondLightSource/FastCS/issues/123
            # * Make 1D scalar array for 1D shapes.
            #     This will require converting from np.int32 to "ai"
            #     if len(shape) == 1:
            #         return NTScalarArray(convert np.datatype32 to string "ad")
            # * Add an option for allowing shape to change, if so we will
            #   use an NDArray here even if shape is 1D

            return NTNDArray()
        case Table(structured_dtype):
            # TODO: `NTEnum/NTNDArray/NTTable.wrap` don't accept extra fields until
            # https://github.com/epics-base/p4p/issues/166
            return NTTable(
                columns=_table_with_numpy_dtypes_to_p4p_dtypes(structured_dtype)
            )
        case _:
            raise RuntimeError(f"Datatype `{attribute.datatype}` unsupported in P4P.")


def cast_from_p4p_value(attribute: Attribute[T], value: object) -> T:
    match attribute.datatype:
        case Enum():
            return attribute.datatype.validate(attribute.datatype.members[value.index])
        case Waveform(shape=shape):
            # p4p sends a flattened array
            assert value.shape == (math.prod(shape),)
            return attribute.datatype.validate(value.reshape(attribute.datatype.shape))
        case Table(structured_dtype):
            assert isinstance(value, np.ndarray)
            return attribute.datatype.validate(np.array(value, dtype=structured_dtype))
        case attribute.datatype if issubclass(
            type(attribute.datatype), P4P_ALLOWED_DATATYPES
        ):
            return attribute.datatype.validate(value)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {attribute.datatype}")


def p4p_alarm_states(
    severity: int = NO_ALARM_SEVERITY,
    status: int = NO_ALARM_STATUS,
    message: str = "",
) -> dict:
    return {
        "alarm": {
            "severity": severity,
            "status": status,
            "message": message,
        },
    }


def p4p_timestamp_now() -> dict:
    now = time.time()
    seconds_past_epoch = int(now)
    nanoseconds = int((now - seconds_past_epoch) * 1e9)
    return {
        "timeStamp": {
            "secondsPastEpoch": seconds_past_epoch,
            "nanoseconds": nanoseconds,
        }
    }


def _p4p_check_numerical_for_alarm_states(
    min_alarm: float | None, max_alarm: float | None, value: T
) -> dict:
    low = None if min_alarm is None else value < min_alarm  # type: ignore
    high = None if max_alarm is None else value > max_alarm  # type: ignore
    severity = (
        MAJOR_ALARM_SEVERITY
        if high not in (None, False) or low not in (None, False)
        else NO_ALARM_SEVERITY
    )
    status, message = NO_ALARM_SEVERITY, "No alarm."
    if low:
        status, message = RECORD_ALARM_STATUS, "Below minimum."
    if high:
        status, message = RECORD_ALARM_STATUS, "Above maximum."
    return p4p_alarm_states(severity, status, message)


def cast_to_p4p_value(attribute: Attribute[T], value: T) -> object:
    match attribute.datatype:
        case Enum():
            return {
                "index": attribute.datatype.index_of(value),
                "choices": [member.name for member in attribute.datatype.members],
            }
        case Waveform():
            return attribute.datatype.validate(value)
        case Table():
            return attribute.datatype.validate(value)

        case datatype if issubclass(type(datatype), P4P_ALLOWED_DATATYPES):
            record_fields = {"value": datatype.validate(value)}
            if attribute.description is not None:
                record_fields["description"] = attribute.description  # type: ignore
            if isinstance(datatype, (Float | Int)):
                record_fields.update(
                    _p4p_check_numerical_for_alarm_states(
                        datatype.min_alarm,
                        datatype.max_alarm,
                        value,
                    )
                )
            else:
                record_fields.update(p4p_alarm_states())

            record_fields.update(
                {k: v for k, v in asdict(datatype).items() if v is not None}
            )
            record_fields.update(p4p_timestamp_now())
            return get_p4p_type(attribute).wrap(record_fields)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {attribute.datatype}")
