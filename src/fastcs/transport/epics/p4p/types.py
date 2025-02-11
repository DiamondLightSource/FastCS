import asyncio
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
from numpy.typing import DTypeLike
from p4p import Type, Value
from p4p.nt import NTEnum, NTNDArray, NTScalar, NTTable
from p4p.nt.common import alarm, timeStamp
from p4p.server import ServerOperation, StaticProvider
from p4p.server.asyncio import SharedPV

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController
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
_RECORD_ALARM_STATUS = 3
_NO_ALARM_STATUS = 0
_MAJOR_ALARM_SEVERITY = 2
_NO_ALARM_SEVERITY = 0

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


def _get_nt_scalar_from_attribute(
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
        # `NTEnum/NTNDArray/NTTable.wrap` don't accept extra fields until
        # https://github.com/epics-base/p4p/issues/166
        case Enum():
            return NTEnum()
        case Waveform():
            # TODO: Make 1D scalar array for 1D shapes
            # This will require converting from np.int32 to "ai"
            # if len(shape) == 1:
            #     return NTScalarArray(convert np.datatype32 to string "ad")
            # TODO: Add an option for allowing shape to change, if so we will
            # use an NDArray here even if shape is 1D

            return NTNDArray()
        case Table(structured_dtype):
            return NTTable(
                columns=_table_with_numpy_dtypes_to_p4p_dtypes(structured_dtype)
            )
        case _:
            raise RuntimeError(f"Datatype `{attribute.datatype}` unsupported in P4P.")


def _cast_from_p4p_type(attribute: Attribute[T], value: object) -> T:
    match attribute.datatype:
        case Enum():
            return attribute.datatype.validate(attribute.datatype.members[value.index])
        case attribute.datatype if issubclass(
            type(attribute.datatype), P4P_ALLOWED_DATATYPES
        ):
            return attribute.datatype.validate(value)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {attribute.datatype}")


def _p4p_alarm_states(
    severity: int = _NO_ALARM_SEVERITY,
    status: int = _NO_ALARM_STATUS,
    message: str = "",
) -> dict:
    return {
        "alarm": {
            "severity": severity,
            "status": status,
            "message": message,
        },
    }


def _p4p_timestamp_now() -> dict:
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
        _MAJOR_ALARM_SEVERITY
        if high is not None or low is not None
        else _NO_ALARM_SEVERITY
    )
    status, message = _NO_ALARM_SEVERITY, "No alarm."
    if low:
        status, message = _RECORD_ALARM_STATUS, "Below minimum."
    if high:
        status, message = _RECORD_ALARM_STATUS, "Above maximum."
    return _p4p_alarm_states(severity, status, message)


def _cast_to_p4p_type(attribute: Attribute[T], value: T) -> object:
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
                record_fields.update(_p4p_alarm_states())

            record_fields.update(
                {k: v for k, v in asdict(datatype).items() if v is not None}
            )
            record_fields.update(_p4p_timestamp_now())
            return _get_nt_scalar_from_attribute(attribute).wrap(record_fields)  # type: ignore
        case _:
            raise ValueError(f"Unsupported datatype {attribute.datatype}")


class AttrWHandler:
    def __init__(self, attr_w: AttrW | AttrRW):
        self._attr_w = attr_w

    async def put(self, pv: SharedPV, op: ServerOperation):
        value = op.value()
        if isinstance(value, list):
            assert isinstance(self._attr_w.datatype, Table)
            raw_value = np.array(
                [tuple(labelled_row.values()) for labelled_row in value],
                dtype=self._attr_w.datatype.structured_dtype,
            )
        else:
            raw_value = value.raw.value

        cast_value = _cast_from_p4p_type(self._attr_w, raw_value)
        await self._attr_w.process_without_display_update(cast_value)

        pv.post(_cast_to_p4p_type(self._attr_w, cast_value))
        op.done()


def make_shared_pv(attribute: Attribute) -> SharedPV:
    initial_value = (
        attribute.get()
        if isinstance(attribute, AttrRW | AttrR)
        else attribute.datatype.initial_value
    )
    kwargs = {
        "nt": _get_nt_scalar_from_attribute(attribute),
        "initial": _cast_to_p4p_type(attribute, initial_value),
    }

    if isinstance(attribute, (AttrW | AttrRW)):
        kwargs["handler"] = AttrWHandler(attribute)

    shared_pv = SharedPV(**kwargs)

    if isinstance(attribute, (AttrR | AttrRW)):
        shared_pv.post(_cast_to_p4p_type(attribute, attribute.get()))

        async def on_update(value):
            shared_pv.post(_cast_to_p4p_type(attribute, value))

        attribute.set_update_callback(on_update)

    return shared_pv


class CommandHandler:
    def __init__(self, command: Callable):
        self._command = command
        self._task_started_event = asyncio.Event()

    async def _run_command(self, pv: SharedPV):
        self._task_started_event.set()
        self._task_started_event.clear()

        kwargs = {}
        try:
            await self._command()
        except Exception as e:
            kwargs.update(
                _p4p_alarm_states(_MAJOR_ALARM_SEVERITY, _RECORD_ALARM_STATUS, str(e))
            )
        else:
            kwargs.update(_p4p_alarm_states())

        value = NTScalar("?").wrap({"value": False, **kwargs})
        timestamp = time.time()
        pv.close()
        pv.open(value, timestamp=timestamp)
        pv.post(value, timestamp=timestamp)

    async def put(self, pv: SharedPV, op: ServerOperation):
        value = op.value()
        raw_value = value.raw.value

        if raw_value is True:
            asyncio.create_task(self._run_command(pv))
            await self._task_started_event.wait()

        # Flip to true once command task starts
        pv.post(value, timestamp=time.time())
        op.done()


def make_command_pv(command: Callable) -> SharedPV:
    shared_pv = SharedPV(
        nt=NTScalar("?"),
        initial=False,
        handler=CommandHandler(command),
    )

    return shared_pv


AccessModeType = Literal["r", "w", "rw", "d", "x"]

PviName = str


@dataclass
class _PviFieldInfo:
    pv: str
    access: AccessModeType

    # Controller type to check all pvi "d" in a group are the same type.
    controller_t: type[BaseController] | None

    # Number for the int value on the end of the pv.
    # We need this so that a pvi group with Child1 and Child3 controllers gives
    # structure[] child
    #     structure
    #         (none)
    #     structure
    #         string d P4P_TEST_DEVICE:Child1:PVI
    #     structure
    #         (none)
    #     structure
    #         string d P4P_TEST_DEVICE:Child3:PVI
    number: int | None = None


@dataclass
class _PviBlockInfo:
    field_infos: dict[str, list[_PviFieldInfo]]
    description: str | None


def _pv_to_pvi_field(pv: str) -> tuple[str, int | None]:
    leaf = pv.rsplit(":", maxsplit=1)[-1].lower()
    match = re.search(r"(\d+)$", leaf)
    number = int(match.group(1)) if match else None
    string_without_number = re.sub(r"\d+$", "", leaf)
    return string_without_number, number


class PviTree:
    def __init__(self):
        self._pvi_info: dict[PviName, _PviBlockInfo] = {}

    def add_block(
        self,
        block_pv: str,
        description: str | None,
        controller_t: type[BaseController] | None = None,
    ):
        pvi_name, number = _pv_to_pvi_field(block_pv)
        if block_pv not in self._pvi_info:
            self._pvi_info[block_pv] = _PviBlockInfo(
                field_infos={}, description=description
            )

        parent_block_pv = block_pv.rsplit(":", maxsplit=1)[0]

        if parent_block_pv == block_pv:
            return

        if pvi_name not in self._pvi_info[parent_block_pv].field_infos:
            self._pvi_info[parent_block_pv].field_infos[pvi_name] = []
        elif (
            controller_t
            is not (
                other_field := self._pvi_info[parent_block_pv].field_infos[pvi_name][-1]
            ).controller_t
        ):
            raise ValueError(
                f"Can't add `{block_pv}` to pvi group {pvi_name}. "
                f"It represents a {controller_t}, however {other_field.pv} "
                f"represents a {other_field.controller_t}."
            )

        self._pvi_info[parent_block_pv].field_infos[pvi_name].append(
            _PviFieldInfo(
                pv=f"{block_pv}:PVI",
                access="d",
                controller_t=controller_t,
                number=number,
            )
        )

    def add_field(
        self,
        attribute_pv: str,
        access: AccessModeType,
    ):
        pvi_name, _ = _pv_to_pvi_field(attribute_pv)
        parent_block_pv = attribute_pv.rsplit(":", maxsplit=1)[0]

        if pvi_name not in self._pvi_info[parent_block_pv].field_infos:
            self._pvi_info[parent_block_pv].field_infos[pvi_name] = []

        self._pvi_info[parent_block_pv].field_infos[pvi_name].append(
            _PviFieldInfo(pv=attribute_pv, access=access, controller_t=None)
        )

    def make_provider(self) -> StaticProvider:
        provider = StaticProvider("PVI")

        for block_pv, block_info in self._pvi_info.items():
            provider.add(
                f"{block_pv}:PVI",
                SharedPV(initial=self._p4p_value(block_info)),
            )
        return provider

    def _p4p_value(self, block_info: _PviBlockInfo) -> Value:
        pvi_structure = []
        for pvi_name, field_infos in block_info.field_infos.items():
            if len(field_infos) == 1:
                field_datatype = [(field_infos[0].access, "s")]
            else:
                assert all(
                    field_info.access == field_infos[0].access
                    for field_info in field_infos
                )
                field_datatype = [
                    (
                        field_infos[0].access,
                        (
                            "S",
                            None,
                            [
                                (f"v{field_info.number}", "s")
                                for field_info in field_infos
                            ],
                        ),
                    )
                ]

            substructure = (
                pvi_name,
                (
                    "S",
                    "structure",
                    # If there are multiple field_infos then they ar the same type of
                    # controller.
                    field_datatype,
                ),
            )
            pvi_structure.append(substructure)

        p4p_type = Type(
            [
                ("alarm", alarm),
                ("timeStamp", timeStamp),
                ("display", ("S", None, [("description", "s")])),
                ("value", ("S", "structure", tuple(pvi_structure))),
            ]
        )

        value = {}
        for pvi_name, field_infos in block_info.field_infos.items():
            if len(field_infos) == 1:
                value[pvi_name] = {field_infos[0].access: field_infos[0].pv}
            else:
                value[pvi_name] = {
                    field_infos[0].access: {
                        f"v{field_info.number}": field_info.pv
                        for field_info in field_infos
                    }
                }

        return Value(
            p4p_type,
            {
                **_p4p_alarm_states(),
                **_p4p_timestamp_now(),
                "display": {"description": block_info.description},
                "value": value,
            },
        )
