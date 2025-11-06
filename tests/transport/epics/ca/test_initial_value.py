import asyncio
import enum

import numpy as np
import pytest
from aioca import caget

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsIOCOptions


class InitialEnum(enum.Enum):
    A = 0
    B = 1
    C = 2


class InitialValuesController(Controller):
    int = AttrRW(Int(), initial_value=4)
    float = AttrRW(Float(), initial_value=3.1)
    bool = AttrRW(Bool(), initial_value=True)
    enum = AttrRW(Enum(InitialEnum), initial_value=InitialEnum.B)
    str = AttrRW(String(), initial_value="initial")
    waveform = AttrRW(
        Waveform(np.int64, shape=(10,)),
        initial_value=np.array(range(10), dtype=np.int64),
    )
    int_r = AttrR(Int(), initial_value=5)
    float_r = AttrR(Float(), initial_value=4.1)
    bool_r = AttrR(Bool(), initial_value=False)
    enum_r = AttrR(Enum(InitialEnum), initial_value=InitialEnum.C)
    str_r = AttrR(String(), initial_value="initial_r")
    waveform_r = AttrR(
        Waveform(np.int64, shape=(10,)),
        initial_value=np.array(range(10, 20), dtype=np.int64),
    )
    int_w = AttrW(Int())
    float_w = AttrW(Float())
    bool_w = AttrW(Bool())
    enum_w = AttrW(Enum(InitialEnum))
    str_w = AttrW(String())
    waveform_w = AttrW(Waveform(np.int64, shape=(10,)))


@pytest.mark.forked
@pytest.mark.asyncio
async def test_initial_values_set_in_ca():
    pv_prefix = "SOFTIOC_INITIAL_DEVICE"

    loop = asyncio.get_event_loop()
    fastcs = FastCS(
        InitialValuesController(),
        [EpicsCATransport(ca_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))],
        loop,
    )

    task = asyncio.create_task(fastcs.serve(interactive=False))
    # combine cagets to reduce timeouts

    # AttrRWs
    scalar_sets = await caget(
        [
            f"{pv_prefix}:Int",
            f"{pv_prefix}:Float",
            f"{pv_prefix}:Bool",
            f"{pv_prefix}:Enum",
        ]
    )
    assert scalar_sets == [4, 3.1, 1, 1]
    scalar_rbvs = await caget(
        [
            f"{pv_prefix}:Int_RBV",
            f"{pv_prefix}:Float_RBV",
            f"{pv_prefix}:Bool_RBV",
            f"{pv_prefix}:Enum_RBV",
        ]
    )
    assert scalar_rbvs == [4, 3.1, 1, 1]
    assert (await caget(f"{pv_prefix}:Str")).tobytes() == b"initial\0"
    assert np.array_equal((await caget(f"{pv_prefix}:Waveform")), list(range(10)))
    assert (await caget(f"{pv_prefix}:Str_RBV")).tobytes() == b"initial\0"
    assert np.array_equal((await caget(f"{pv_prefix}:Waveform_RBV")), list(range(10)))

    # AttrRs
    scalars = await caget(
        [
            f"{pv_prefix}:IntR",
            f"{pv_prefix}:FloatR",
            f"{pv_prefix}:BoolR",
            f"{pv_prefix}:EnumR",
        ]
    )
    assert scalars == [5, 4.1, 0, 2]
    assert (await caget(f"{pv_prefix}:StrR")).tobytes() == b"initial_r\0"
    assert np.array_equal((await caget(f"{pv_prefix}:WaveformR")), list(range(10, 20)))

    # Check AttrWs use the datatype initial value
    w_scalars = await caget(
        [
            f"{pv_prefix}:IntW",
            f"{pv_prefix}:FloatW",
            f"{pv_prefix}:BoolW",
            f"{pv_prefix}:EnumW",
        ]
    )
    assert w_scalars == [0, 0, 0, 0]
    assert (await caget(f"{pv_prefix}:StrW")).tobytes() == b"\0"
    # initial waveforms not set with zeros
    assert np.array_equal((await caget(f"{pv_prefix}:WaveformW")), [])

    task.cancel()
