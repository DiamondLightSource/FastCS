from functools import partial

import pytest

from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import Int, String


@pytest.mark.asyncio
async def test_attributes():
    device = {"state": "Idle", "number": 1, "count": False}
    ui = {"state": "", "number": 0, "count": False}

    async def update_ui(value, key):
        ui[key] = value

    async def send(value, key):
        device[key] = value

    async def device_add():
        device["number"] += 1

    attr_r = AttrR(String())
    attr_r.set_update_callback(partial(update_ui, key="state"))
    await attr_r.set(device["state"])
    assert ui["state"] == "Idle"

    attr_rw = AttrRW(Int())
    attr_rw.set_process_callback(partial(send, key="number"))
    attr_rw.set_write_display_callback(partial(update_ui, key="number"))
    await attr_rw.process(2)
    assert device["number"] == 2
    assert ui["number"] == 2
