from functools import partial

import pytest
from pytest_mock import MockerFixture

from fastcs.attributes import AttrR, AttrRW, AttrW
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


@pytest.mark.asyncio
async def test_simple_handler_w(mocker: MockerFixture):
    attr = AttrW(Int())
    update_display_mock = mocker.patch.object(attr, "update_display_without_process")

    # This is called by the transport when it receives a put
    await attr.sender.put(mocker.ANY, attr, 1)

    # The callback to update the transport display should be called
    update_display_mock.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_simple_handler_rw(mocker: MockerFixture):
    attr = AttrRW(Int())
    update_display_mock = mocker.patch.object(attr, "update_display_without_process")
    set_mock = mocker.patch.object(attr, "set")

    await attr.sender.put(mocker.ANY, attr, 1)

    update_display_mock.assert_called_once_with(1)
    # The Sender of the attribute should just set the value on the attribute
    set_mock.assert_awaited_once_with(1)
