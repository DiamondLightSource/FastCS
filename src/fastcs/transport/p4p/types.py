import asyncio
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Literal, TypedDict

from p4p import Type, Value
from p4p.nt import NTEnum, NTNDArray, NTScalar
from p4p.nt.common import alarm, timeStamp
from p4p.server import ServerOperation, StaticProvider
from p4p.server.asyncio import SharedPV

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Enum, Float, Int, String, T, Waveform

P4P_ALLOWED_DATATYPES = (Int, Float, String, Bool, Enum, Waveform)


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


def _get_nt_scalar_from_attribute(
    attribute: Attribute,
) -> NTScalar | NTEnum | NTNDArray:
    match attribute.datatype:
        case Int():
            return _P4P_INT
        case Float():
            return _P4P_FLOAT
        case String():
            return _P4P_STRING
        case Bool():
            return _P4P_BOOL
        # `NTEnum/NTNDArray.wrap` don't accept extra fields until
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
        self._last_task: asyncio.Future | None = None
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

        if (
            raw_value is False
            and self._last_task is not None
            and not self._last_task.done()
        ):
            self._last_task.cancel()
            try:
                await self._last_task
            except asyncio.CancelledError:
                pass
        elif (
            raw_value is True
            and self._last_task is not None
            and not self._last_task.done()
        ):
            raise RuntimeError(
                f"{self._command} is already running, received signal to run it again."
            )

        elif not isinstance(raw_value, bool):
            raise ValueError(
                "Command PVs are `True` while the command is running, `False` once "
                "it's finished. `False` can be put to stop the running command."
            )

        if raw_value is True:
            self._last_task = asyncio.create_task(self._run_command(pv))
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


AccessModeType = Literal["r", "w", "rw", "pvi", "command"]


class _PviFieldInfo(TypedDict):
    pv: str
    access: AccessModeType


class _PviBlockDisplay(TypedDict):
    description: str


class _PviBlockInfo(TypedDict):
    display: _PviBlockDisplay
    value: list[_PviFieldInfo]


class PviTree:
    _P4PType = Type(
        [
            ("alarm", alarm),
            ("timeStamp", timeStamp),
            ("display", ("S", None, [("description", "s")])),
            (
                "value",
                ("aS", None, [("pv", "s"), ("access", "s")]),
            ),
        ]
    )

    def __init__(self):
        self._pvi_info: dict[str, _PviBlockInfo] = {}

    def add_block(self, block_pv: str, description: str | None = None):
        if block_pv not in self._pvi_info:
            self._pvi_info[block_pv] = _PviBlockInfo(
                display=_PviBlockDisplay(description=(description or "")), value=[]
            )
        elif (
            description is not None
            and self._pvi_info[block_pv]["display"]["description"] != description
        ):
            # Allows field info to be added before the block info.
            # Not needed in the case of `controller.get_mappings`,
            # but still useful.
            self._pvi_info[block_pv]["display"]["description"] = description

        parent_pv = block_pv.rsplit(":", maxsplit=1)[0]
        if parent_pv != block_pv:
            self._pvi_info[parent_pv]["value"].append(
                _PviFieldInfo(pv=f"{block_pv}:PVI", access="pvi")
            )

    def add_field(self, attribute_pv: str, access: AccessModeType):
        block_pv = attribute_pv.rsplit(":", maxsplit=1)[0]
        if block_pv not in self._pvi_info:
            self._pvi_info[block_pv] = _PviBlockInfo(
                display=_PviBlockDisplay(description=""), value=[]
            )
        self._pvi_info[block_pv]["value"].append(
            _PviFieldInfo(pv=attribute_pv, access=access)
        )

    def make_provider(self) -> StaticProvider:
        provider = StaticProvider("PVI")
        for block_pv, block_pvi_info in self._pvi_info.items():
            provider.add(
                f"{block_pv}:PVI",
                SharedPV(initial=self._p4p_value(block_pvi_info)),
            )
        return provider

    def _p4p_value(self, block_pvi_info: _PviBlockInfo) -> Value:
        return Value(
            self._P4PType,
            {**_p4p_alarm_states(), **_p4p_timestamp_now(), **block_pvi_info},
        )
