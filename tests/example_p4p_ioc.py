import asyncio
import enum
from dataclasses import dataclass

import numpy as np

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller, ControllerVector
from fastcs.datatypes import Bool, Enum, Float, Int, T, Table, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.options import (
    EpicsIOCOptions,
)
from fastcs.transport.epics.pva.transport import EpicsPVATransport
from fastcs.wrappers import command, scan


@dataclass
class SimpleAttributeIORef(AttributeIORef):
    pass


class SimpleAttributeIO(AttributeIO[T, SimpleAttributeIORef]):
    async def send(self, attr: AttrW[T, SimpleAttributeIORef], value):
        if isinstance(attr, AttrRW):
            await attr.update(value)


class FEnum(enum.Enum):
    A = 0
    B = 1
    C = "VALUES ARE ARBITRARY"
    D = 2
    E = 5


class ParentController(Controller):
    description = "some controller"
    a: AttrRW = AttrRW(
        Int(max=400_000, max_alarm=40_000), io_ref=SimpleAttributeIORef()
    )
    b: AttrW = AttrW(Float(min=-1, min_alarm=-0.5), io_ref=SimpleAttributeIORef())

    table: AttrRW = AttrRW(
        Table([("A", np.int32), ("B", "i"), ("C", "?"), ("D", np.float64)]),
        io_ref=SimpleAttributeIORef(),
    )

    def __init__(self, description=None, ios=None):
        super().__init__(description, ios)


class ChildController(Controller):
    fail_on_next_e = True
    c: AttrW = AttrW(Int(), io_ref=SimpleAttributeIORef())

    def __init__(self, description=None, ios=None):
        super().__init__(description, ios)

    @command()
    async def d(self):
        print("D: RUNNING")
        await asyncio.sleep(0.1)
        print("D: FINISHED")
        await self.j.update(self.j.get() + 1)

    e: AttrR = AttrR(Bool(), io_ref=SimpleAttributeIORef())

    @scan(1)
    async def flip_flop(self):
        await self.e.update(not self.e.get())

    f: AttrRW = AttrRW(Enum(FEnum))
    g: AttrRW = AttrRW(Waveform(np.int64, shape=(3,)))
    h: AttrRW = AttrRW(Waveform(np.float64, shape=(3, 3)))

    @command()
    async def i(self):
        print("I: RUNNING")
        await asyncio.sleep(0.1)
        if self.fail_on_next_e:
            self.fail_on_next_e = False
            raise RuntimeError("I: FAILED WITH THIS WEIRD ERROR")
        else:
            self.fail_on_next_e = True
            print("I: FINISHED")
            await self.j.update(self.j.get() + 1)

    j: AttrR = AttrR(Int())


def run(pv_prefix="P4P_TEST_DEVICE"):
    simple_attribute_io = SimpleAttributeIO()
    p4p_options = EpicsPVATransport(epicspva=EpicsIOCOptions(pv_prefix=pv_prefix))
    controller = ParentController(ios=[simple_attribute_io])

    class ChildVector(ControllerVector):
        vector_attribute: AttrR = AttrR(Int())

        def __init__(self, children, description=None):
            super().__init__(children, description)

    sub_controller = ChildVector(
        {
            1: ChildController(
                description="some sub controller", ios=[simple_attribute_io]
            ),
            2: ChildController(
                description="another sub controller", ios=[simple_attribute_io]
            ),
        },
        description="some child vector",
    )

    controller.add_sub_controller("child", sub_controller)

    fastcs = FastCS(controller, [p4p_options])
    fastcs.run()


if __name__ == "__main__":
    run()
