from functools import partial

import pytest
from pytest_mock import MockerFixture

from fastcs.attributes import (
    AttrR,
    AttrRW,
)
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
    attr_r.add_set_callback(partial(update_ui, key="state"))
    await attr_r.set(device["state"])
    assert ui["state"] == "Idle"

    attr_rw = AttrRW(Int())
    attr_rw.add_process_callback(partial(send, key="number"))
    attr_rw.add_write_display_callback(partial(update_ui, key="number"))
    await attr_rw.process(2)
    assert device["number"] == 2
    assert ui["number"] == 2


@pytest.mark.asyncio
async def test_simple_attibute_io_rw(mocker: MockerFixture):
    attr = AttrRW(Int())

    attr.update_display_without_process = mocker.MagicMock(
        wraps=attr.update_display_without_process
    )
    attr.set = mocker.MagicMock(wraps=attr.set)

    assert attr.sender
    # This is called by the transport when it receives a put
    await attr.process(1)

    # SimpleAttributeIO attribute should just set the value on the attribute
    attr.update_display_without_process.assert_called_once_with(1)
    attr.set.assert_called_once_with(1)
    assert attr.get() == 1
