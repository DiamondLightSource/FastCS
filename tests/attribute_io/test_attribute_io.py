from dataclasses import dataclass
from typing import Generic

import pytest

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Float, Int, T


# async def test_attribute_io(mocker: MockerFixture):
@pytest.mark.asyncio
async def test_attribute_io():
    @dataclass
    class MyAttributeIORef(AttributeIORef):
        cool: int

    class MyAttributeIO(AttributeIO[int, MyAttributeIORef]):
        async def update(self, attr: AttrR[Int, MyAttributeIORef]):
            print("I am updating", self.ref_type, attr.io_ref.cool)

    class MyController(Controller):
        # what if we hinted something like
        # io_classes: MyAttributeIO | MyOtherAttributeIO
        # and then we construct them in the __init__ per controller?
        # I guess this is bad as we can't share between controllers
        # i really just want to avoid making devs invoke super...
        # or maybe that's not a big deal...
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
            # assume the device is always incrementing every parameter by 1
            await attr.set(attr.get() + 1)
            pass

        async def send(self, attr: AttrW[T], value) -> None:
            # why does this not get called...
            print(attr.ref.min, value)
            if (
                attr.ref.read_only
            ):  # TODO, this isn't necessary as we can not call process on this anyway
                raise RuntimeError(f"Could not set read only attribute {attr.ref.name}")

            if attr.ref.min is not None and value < min:
                raise RuntimeError(
                    f"Could not set {attr.ref.name} to {value}, min is {attr.ref.min}"
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
    assert c.ro_int_parameter.get() == 6
    # with
    await c.int_parameter.process(-10)


def test_update_period_respected():
    raise NotImplementedError
