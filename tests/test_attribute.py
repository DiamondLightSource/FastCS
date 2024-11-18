from functools import partial

import numpy as np
import pytest

from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import Int, String, WaveForm


@pytest.mark.asyncio
async def test_attributes():
    device = {"state": "Idle", "number": 1, "count": False, "array": None}
    ui = {"state": "", "number": 0, "count": False}

    async def update_ui(value, key):
        ui[key] = value

    async def send(value, key):
        device[key] = value

    attr_r = AttrR(String())
    attr_r.set_update_callback(partial(update_ui, key="state"))
    await attr_r.set(device["state"])
    assert ui["state"] == "Idle"

    attr_rw = AttrRW(Int(max=10))
    attr_rw.set_process_callback(partial(send, key="number"))
    attr_rw.set_write_display_callback(partial(update_ui, key="number"))
    await attr_rw.process(10)
    assert device["number"] == 10
    assert ui["number"] == 10
    with pytest.raises(ValueError):
        await attr_rw.set(100)

    attr_rw = AttrRW(WaveForm(np.dtype("int32"), 10))
    attr_rw.set_process_callback(partial(send, key="array"))
    await attr_rw.process(np.array(range(10), dtype="int32"))
    assert np.array_equal(device["array"], np.array(range(10), dtype="int32"))

    with pytest.raises(
        ValueError, match="Waveform length 11 is greater than maximum 10."
    ):
        await attr_rw.process(np.array(range(11), dtype="int32"))
    with pytest.raises(
        ValueError, match="Waveform dtype float64 does not match int32."
    ):
        await attr_rw.process(np.array(range(10), dtype="float64"))
