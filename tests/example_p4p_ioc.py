import asyncio
import enum

import numpy as np

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Bool, Enum, Float, Int, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.options import (
    EpicsBackend,
    EpicsIOCOptions,
    EpicsOptions,
)
from fastcs.wrappers import command, scan


class FEnum(enum.Enum):
    A = 0
    B = 1
    C = "VALUES ARE ARBITRARY"
    D = 2
    E = 5


class ParentController(Controller):
    description = "some controller"
    a: AttrR = AttrR(Int())
    b: AttrRW = AttrRW(Float(min=-1, min_alarm=-0.5))


class ChildController(SubController):
    c: AttrW = AttrW(Int())

    @command()
    async def d(self):
        print("D: RUNNING")
        await asyncio.sleep(1)
        print("D: FINISHED")

    e: AttrR = AttrR(Bool())

    @scan(1)
    async def flip_flop(self):
        await self.e.set(not self.e.get())

    f: AttrRW = AttrRW(Enum(FEnum))
    g: AttrRW = AttrRW(Waveform(np.int64, shape=(3,)))
    h: AttrRW = AttrRW(Waveform(np.float64, shape=(3, 3)))

    @command()
    async def i(self):
        print("I: RUNNING")
        await asyncio.sleep(1)
        raise RuntimeError("I: FAILED WITH THIS WEIRD ERROR")


def run():
    p4p_options = EpicsOptions(
        ioc=EpicsIOCOptions(pv_prefix="P4P_TEST_DEVICE"), backend=EpicsBackend.P4P
    )
    controller = ParentController()
    controller.register_sub_controller(
        "Child1", ChildController(description="some sub controller")
    )
    controller.register_sub_controller(
        "Child2", ChildController(description="another sub controller")
    )
    fastcs = FastCS(controller, [p4p_options])
    fastcs.run()


if __name__ == "__main__":
    run()
