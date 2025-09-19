from dataclasses import dataclass

import pytest
from pytest_mock import MockerFixture

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import (
    AttrR,
)
from fastcs.controller import Controller
from fastcs.datatypes import Int


@pytest.mark.asyncio
async def test_attribute_io(mocker: MockerFixture):
    @dataclass
    class MyAttributeIORef(AttributeIORef):
        cool: int

    class MyAttributeIO(AttributeIO[int, MyAttributeIORef]):
        def __init__(self):
            # i don't really like this pattern of having to call super...
            super().__init__(
                MyAttributeIORef
            )  # i see, so we use the class not an instance of the ref??

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
