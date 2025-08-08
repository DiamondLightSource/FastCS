from functools import partial

import pytest
from pytest_mock import MockerFixture

from fastcs.attributes import (
    AttrHandlerR,
    AttrHandlerRW,
    AttrR,
    AttrRW,
    AttrW,
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
    attr_r.add_update_callback(partial(update_ui, key="state"))
    await attr_r.set(device["state"])
    assert ui["state"] == "Idle"

    attr_rw = AttrRW(Int())
    attr_rw.add_process_callback(partial(send, key="number"))
    attr_rw.add_write_display_callback(partial(update_ui, key="number"))
    await attr_rw.process(2)
    assert device["number"] == 2
    assert ui["number"] == 2


@pytest.mark.asyncio
async def test_simple_handler_rw(mocker: MockerFixture):
    attr = AttrRW(Int())

    attr.update_display_without_process = mocker.MagicMock(
        wraps=attr.update_display_without_process
    )
    attr.set = mocker.MagicMock(wraps=attr.set)

    assert attr.sender
    # This is called by the transport when it receives a put
    await attr.sender.put(attr, 1)

    # The Sender of the attribute should just set the value on the attribute
    attr.update_display_without_process.assert_called_once_with(1)
    attr.set.assert_called_once_with(1)
    assert attr.get() == 1


class SimpleUpdater(AttrHandlerR):
    pass


@pytest.mark.asyncio
async def test_handler_initialise(mocker: MockerFixture):
    handler = AttrHandlerRW()
    handler_mock = mocker.patch.object(handler, "initialise")
    attr = AttrR(Int(), handler=handler)

    ctrlr = mocker.Mock()
    await attr.initialise(ctrlr)

    # The handler initialise method should be called from the attribute
    handler_mock.assert_called_once_with(ctrlr)

    handler = AttrHandlerRW()
    attr = AttrW(Int(), handler=handler)

    # Assert no error in calling initialise on the SimpleHandler default
    await attr.initialise(mocker.ANY)

    handler = SimpleUpdater()
    attr = AttrR(Int(), handler=handler)

    # Assert no error in calling initialise on the TestUpdater handler
    await attr.initialise(mocker.ANY)
