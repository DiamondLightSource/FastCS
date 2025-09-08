import asyncio
import enum

import numpy as np
from aioca import caget

from fastcs.attributes import AttrRW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions


class InitialEnum(enum.Enum):
    A = 0
    B = 1


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


def make_fastcs(pv_prefix: str, controller: Controller) -> FastCS:
    epics_options = EpicsCAOptions(ca_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))
    return FastCS(controller, [epics_options])


def test_initial_values_set_in_ca():
    controller = InitialValuesController()
    pv_prefix = "SOFTIOC_TEST_DEVICE"
    fastcs = make_fastcs(pv_prefix, controller)

    serve = asyncio.ensure_future(fastcs.serve())

    async def _test_cagets():
        await asyncio.sleep(0.1)
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
        assert np.array_equal(
            (await caget(f"{pv_prefix}:Waveform_RBV")), list(range(10))
        )

    test_cagets = asyncio.ensure_future(_test_cagets())

    asyncio.get_event_loop().run_until_complete(
        asyncio.wait_for(test_cagets, timeout=None)
    )

    serve.cancel()
