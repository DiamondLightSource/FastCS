import asyncio
import enum

import numpy as np

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Enum, Float, Int, Table, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.options import (
    EpicsIOCOptions,
)
from fastcs.transport.epics.pva.transport import EpicsPVATransport
from fastcs.wrappers import command, scan


class FEnum(enum.Enum):
    A = 0
    B = 1
    C = "VALUES ARE ARBITRARY"
    D = 2
    E = 5


class ParentController(Controller):
    description = "some controller"
    a: AttrRW = AttrRW(Int(max=400_000, max_alarm=40_000))
    b: AttrW = AttrW(Float(min=-1, min_alarm=-0.5))

    table: AttrRW = AttrRW(
        Table([("A", np.int32), ("B", "i"), ("C", "?"), ("D", np.float64)])
    )


class ChildController(Controller):
    fail_on_next_e = True
    c: AttrW = AttrW(Int())

    @command()
    async def d(self):
        print("D: RUNNING")
        await asyncio.sleep(0.1)
        print("D: FINISHED")
        await self.j.update(self.j.get() + 1)

    e: AttrR = AttrR(Bool())

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
    controller = ParentController()
    controller.a.enable_tracing()
    controller.child1 = ChildController(description="some sub controller")
    controller.child2 = ChildController(description="another sub controller")

    fastcs = FastCS(
        controller, [EpicsPVATransport(pva_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))]
    )
    fastcs.run(interactive=False)


if __name__ == "__main__":
    run()
