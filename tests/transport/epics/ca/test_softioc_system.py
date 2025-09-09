from multiprocessing import Queue

import numpy as np
import pytest
from aioca import caget
from p4p import Value
from p4p.client.thread import Context


def test_ioc(softioc_subprocess: tuple[str, Queue]):
    pv_prefix, _ = softioc_subprocess
    ctxt = Context("pva")

    _parent_pvi = ctxt.get(f"{pv_prefix}:PVI")
    assert isinstance(_parent_pvi, Value)
    parent_pvi = _parent_pvi.todict()
    assert all(f in parent_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert parent_pvi["display"] == {"description": "The records in this controller"}
    assert parent_pvi["value"] == {
        "a": {"r": f"{pv_prefix}:A"},
        "b": {"r": f"{pv_prefix}:B_RBV", "w": f"{pv_prefix}:B"},
        "child": {"d": f"{pv_prefix}:Child:PVI"},
    }

    child_pvi_pv = parent_pvi["value"]["child"]["d"]
    _child_pvi = ctxt.get(child_pvi_pv)
    assert isinstance(_child_pvi, Value)
    child_pvi = _child_pvi.todict()
    assert all(f in child_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert child_pvi["display"] == {"description": "The records in this controller"}
    assert child_pvi["value"] == {
        "c": {"w": f"{pv_prefix}:Child:C"},
        "d": {"x": f"{pv_prefix}:Child:D"},
    }


@pytest.mark.asyncio
async def test_initial_values_set_in_ca(initial_softioc_subprocess):
    pv_prefix, _ = initial_softioc_subprocess
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
    return
    assert w_scalars == [0, 0, 0, 0]
    assert (await caget(f"{pv_prefix}:StrW")).tobytes() == b"\0"
    assert np.array_equal((await caget(f"{pv_prefix}:WaveformW")), 10 * [0])
