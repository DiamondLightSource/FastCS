from functools import partial

import numpy as np
import pytest
from pytest_mock import MockerFixture

from fastcs.attributes import AttrHandlerR, AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.datatypes import Enum, Float, Int, String, Waveform


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
async def test_simple_handler_w(mocker: MockerFixture):
    attr = AttrW(Int())
    update_display_mock = mocker.patch.object(attr, "update_display_without_process")

    # This is called by the transport when it receives a put
    await attr.sender.put(attr, 1)

    # The callback to update the transport display should be called
    update_display_mock.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_simple_handler_rw(mocker: MockerFixture):
    attr = AttrRW(Int())
    update_display_mock = mocker.patch.object(attr, "update_display_without_process")
    set_mock = mocker.patch.object(attr, "set")

    await attr.sender.put(attr, 1)

    update_display_mock.assert_called_once_with(1)
    # The Sender of the attribute should just set the value on the attribute
    set_mock.assert_awaited_once_with(1)


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


@pytest.mark.parametrize(
    ["datatype", "init_args", "value"],
    [
        (Int, {"min": 1}, 0),
        (Int, {"max": -1}, 0),
        (Float, {"min": 1}, 0.0),
        (Float, {"max": -1}, 0.0),
        (Float, {}, 0),
        (String, {}, 0),
        (Enum, {"enum_cls": int}, 0),
        (Waveform, {"array_dtype": "U64", "shape": (1,)}, np.ndarray([1])),
        (Waveform, {"array_dtype": "float64", "shape": (1, 1)}, np.ndarray([1])),
    ],
)
def test_validate(datatype, init_args, value):
    with pytest.raises(ValueError):
        datatype(**init_args).validate(value)
