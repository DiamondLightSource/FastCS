import asyncio
import time
from collections.abc import Callable

import numpy as np
from p4p import Value
from p4p.nt import NTEnum, NTNDArray, NTScalar, NTTable
from p4p.server import ServerOperation
from p4p.server.asyncio import SharedPV

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.datatypes import Table

from .types import (
    MAJOR_ALARM_SEVERITY,
    RECORD_ALARM_STATUS,
    cast_from_p4p_value,
    cast_to_p4p_value,
    make_p4p_type,
    p4p_alarm_states,
)


class WritePvHandler:
    def __init__(self, attr_w: AttrW | AttrRW):
        self._attr_w = attr_w

    async def put(self, pv: SharedPV, op: ServerOperation):
        value = op.value()
        if isinstance(self._attr_w.datatype, Table):
            assert isinstance(value, list)
            raw_value = np.array(
                [tuple(labelled_row.values()) for labelled_row in value],
                dtype=self._attr_w.datatype.structured_dtype,
            )
        elif hasattr(value, "raw"):
            raw_value = value.raw.value
        else:
            raw_value = value.todict()["value"]

        cast_value = cast_from_p4p_value(self._attr_w, raw_value)

        await self._attr_w.process_without_display_update(cast_value)
        if type(self._attr_w) is AttrW:
            # For AttrRW a post is done from the `_process_callback`.
            pv.post(cast_to_p4p_value(self._attr_w, cast_value))
        op.done()


class CommandPvHandler:
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
                p4p_alarm_states(MAJOR_ALARM_SEVERITY, RECORD_ALARM_STATUS, str(e))
            )
        else:
            kwargs.update(p4p_alarm_states())

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


def make_shared_pv(attribute: Attribute) -> SharedPV:
    initial_value = (
        attribute.get()
        if isinstance(attribute, AttrRW | AttrR)
        else attribute.datatype.initial_value
    )

    type_ = make_p4p_type(attribute)
    kwargs = {"initial": cast_to_p4p_value(attribute, initial_value)}
    if isinstance(type_, (NTEnum | NTNDArray | NTTable)):
        kwargs["nt"] = type_
    else:

        def _wrap(value: dict):
            return Value(type_, value)

        kwargs["wrap"] = _wrap

    if isinstance(attribute, AttrW):
        kwargs["handler"] = WritePvHandler(attribute)

    shared_pv = SharedPV(**kwargs)

    if isinstance(attribute, AttrR):
        shared_pv.post(cast_to_p4p_value(attribute, attribute.get()))

        async def on_update(value):
            shared_pv.post(cast_to_p4p_value(attribute, value))

        attribute.set_update_callback(on_update)

    return shared_pv


def make_command_pv(command: Callable) -> SharedPV:
    shared_pv = SharedPV(
        nt=NTScalar("?"),
        initial=False,
        handler=CommandPvHandler(command),
    )

    return shared_pv
