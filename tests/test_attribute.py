from dataclasses import dataclass
from functools import partial
from typing import Generic

import pytest
from pytest_mock import MockerFixture

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import (
    AttrR,
    AttrRW,
    AttrW,
)
from fastcs.controller import Controller
from fastcs.datatypes import Float, Int, String, T


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

    # This is called by the transport when it receives a put
    await attr.process(1)

    # SimpleAttributeIO attribute should just set the value on the attribute
    attr.update_display_without_process.assert_called_once_with(1)
    attr.set.assert_called_once_with(1)
    assert attr.get() == 1


@pytest.mark.asyncio
async def test_attribute_io():
    @dataclass
    class MyAttributeIORef(AttributeIORef):
        cool: int

    class MyAttributeIO(AttributeIO[int, MyAttributeIORef]):
        async def update(self, attr: AttrR[Int, MyAttributeIORef]):
            print("I am updating", self.ref_type, attr.io_ref.cool)

    class MyController(Controller):
        my_attr = AttrR(Int(), io_ref=MyAttributeIORef(cool=5))
        your_attr = AttrR(Int(), io_ref=MyAttributeIORef(cool=10))

        def __init__(self):
            super().__init__(ios=[MyAttributeIO()])

    c = MyController()

    class ControllerNoIO(Controller):
        my_attr = AttrR(Int(), io_ref=MyAttributeIORef(cool=5))

    with pytest.raises(AssertionError, match="does not have an AttributeIO"):
        ControllerNoIO()
    # TODO, is it okay that we need to initialise the controller
    # before the callbacks get assigned?
    await c.initialise()
    await c.attribute_initialise()
    await c.my_attr.update()


@pytest.mark.asyncio()
async def test_dynamic_attribute_io_specification():
    example_introspection_response = [
        {
            "name": "int_parameter",
            "dtype": "int",
            "min": 0,
            "max": 100,
            "value": 5,
            "read_only": False,
        },
        {"name": "ro_int_parameter", "dtype": "int", "value": 10, "read_only": True},
        {
            "name": "float_parameter",
            "dtype": "float",
            "max": 1000.0,
            "value": 7.5,
            "read_only": False,
        },
    ]

    @dataclass
    class DemoParameterAttributeIORef(AttributeIORef, Generic[T]):
        name: str
        min: T | None = None
        max: T | None = None
        read_only: bool = False

    class DemoParameterAttributeIO(AttributeIO[T, DemoParameterAttributeIORef]):
        async def update(self, attr: AttrR[T]):
            # OK, so this doesn't really work when we have min and maxes...
            await attr.set(attr.get() + 1)

        async def send(self, attr: AttrW[T], value) -> None:
            if (
                attr.io_ref.read_only
            ):  # TODO, this isn't necessary as we can not call process on this anyway
                raise RuntimeError(
                    f"Could not set read only attribute {attr.io_ref.name}"
                )

            if (io_min := attr.io_ref.min) is not None and value < io_min:
                raise RuntimeError(
                    f"Could not set {attr.io_ref.name} to {value}, "
                    f"min is {attr.io_ref.min}"
                )

            if (io_max := attr.io_ref.max) is not None and value > io_max:
                raise RuntimeError(
                    f"Could not set {attr.io_ref.name} to {value}, "
                    f"max is {attr.io_ref.max}"
                )

    class DemoParameterController(Controller):
        async def initialise(self):
            dtype_mapping = {"int": Int(), "float": Float()}
            for parameter_response in example_introspection_response:
                try:
                    ro = parameter_response["read_only"]
                    ref = DemoParameterAttributeIORef(
                        name=parameter_response["name"],
                        min=parameter_response.get("min", None),
                        max=parameter_response.get("max", None),
                        read_only=ro,
                    )
                    attr_class = AttrR if ro else AttrRW
                    attr = attr_class(
                        datatype=dtype_mapping[parameter_response["dtype"]],
                        io_ref=ref,
                        initial_value=parameter_response.get("value", None),
                    )

                    self.attributes[ref.name] = attr
                    setattr(self, ref.name, attr)

                except Exception as e:
                    print(
                        "Exception constructing attribute from parameter response:",
                        parameter_response,
                        e,
                    )

    c = DemoParameterController(ios=[DemoParameterAttributeIO()])
    await c.initialise()
    await c.attribute_initialise()
    await c.ro_int_parameter.update()
    assert c.ro_int_parameter.get() == 11
    with pytest.raises(
        RuntimeError, match="Could not set int_parameter to -10, min is 0"
    ):
        await c.int_parameter.process(-10)

    with pytest.raises(
        RuntimeError, match="Could not set int_parameter to 101, max is 100"
    ):
        await c.int_parameter.process(101)
