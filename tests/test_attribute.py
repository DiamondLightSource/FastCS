from dataclasses import dataclass
from functools import partial
from typing import Generic, TypeVar

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

NumberT = TypeVar("NumberT", int, float)


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

    # without io/ref should just set the value on the attribute
    attr.update_display_without_process.assert_called_once_with(1)
    attr.set.assert_called_once_with(1)
    assert attr.get() == 1


@pytest.mark.asyncio
async def test_attribute_io():
    @dataclass
    class MyAttributeIORef(AttributeIORef):
        cool: int

    class MyAttributeIO(AttributeIO[int, MyAttributeIORef]):
        async def update(self, attr: AttrR[T, MyAttributeIORef]):
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
    class DemoParameterAttributeIORef(AttributeIORef, Generic[NumberT]):
        name: str
        # TODO, this is weird, we should just use the attributes's min and max fields
        min: NumberT | None = None
        max: NumberT | None = None
        read_only: bool = False

    class DemoParameterAttributeIO(AttributeIO[NumberT, DemoParameterAttributeIORef]):
        async def update(
            self,
            attr: AttrR[NumberT, DemoParameterAttributeIORef],
        ):
            # OK, so this doesn't really work when we have min and maxes...
            await attr.set(attr.get() + 1)

        async def send(
            self,
            attr: AttrW[NumberT, DemoParameterAttributeIORef],
            value: NumberT,
        ) -> None:
            if (
                attr.io_ref.read_only
            ):  # TODO, this isn't necessary as we can not call process on this anyway
                raise RuntimeError(
                    f"Could not set read only attribute {attr.io_ref.name}"
                )

            if (io_min := attr.io_ref.min) is not None and value < io_min:
                raise RuntimeError(
                    f"Could not set {attr.io_ref.name} to {value}, min is {io_min}"
                )

            if (io_max := attr.io_ref.max) is not None and value > io_max:
                raise RuntimeError(
                    f"Could not set {attr.io_ref.name} to {value}, max is {io_max}"
                )
            # TODO: we should always end send with a update_display_without_process...

    class DemoParameterController(Controller):
        ro_int_parameter: AttrR
        int_parameter: AttrRW
        float_parameter: AttrRW  # hint to satisfy pyright

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


@pytest.mark.asyncio
async def test_attribute_io_defaults(mocker: MockerFixture):
    class MyController(Controller):
        no_ref = AttrRW(Int())
        base_class_ref = AttrRW(Int(), io_ref=AttributeIORef())

    with pytest.raises(
        AssertionError,
        match="MyController does not have an AttributeIO to handle AttributeIORef",
    ):
        c = MyController()

    class SimpleAttributeIO(AttributeIO[T, AttributeIORef]):
        async def update(self, attr):
            await attr.set(100)

    with pytest.raises(
        RuntimeError, match="More than one AttributeIO class handles AttributeIORef"
    ):
        MyController(ios=[AttributeIO(), SimpleAttributeIO()])

    # we need to explicitly pass an AttributeIO if we want to handle instances of
    # the AttributeIORef base class
    c = MyController(ios=[AttributeIO()])
    assert not c.no_ref.has_io_ref()
    assert c.base_class_ref.has_io_ref()

    await c.initialise()
    await c.attribute_initialise()

    with pytest.raises(NotImplementedError):
        await c.base_class_ref.update()

    with pytest.raises(NotImplementedError):
        await c.base_class_ref.process(25)

    # There is a difference between providing an AttributeIO for the default
    # AttributeIORef class and not specifying the io_ref for an Attribute
    # default callbacks are not provided by AttributeIO subclasses

    with pytest.raises(
        RuntimeError, match="Can't call update on Attributes without an io_ref"
    ):
        await c.no_ref.update()

    process_spy = mocker.spy(c.no_ref, "update_display_without_process")
    # calls callback which calls update_display_without_process
    # TODO: reconsider if this is what we want the default case to be
    # as process already calls that
    await c.no_ref.process_without_display_update(40)
    process_spy.assert_called_with(40)

    process_spy.assert_called_once_with(40)

    c2 = MyController(ios=[SimpleAttributeIO()])

    await c2.initialise()
    await c2.attribute_initialise()

    assert c2.base_class_ref.get() == 0
    await c2.base_class_ref.update()
    assert c2.base_class_ref.get() == 100
