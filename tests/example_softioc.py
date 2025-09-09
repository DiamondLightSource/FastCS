import enum

import numpy as np

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String, Waveform
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.wrappers import command


class InitialEnum(enum.Enum):
    A = 0
    B = 1


class ParentController(Controller):
    a: AttrR = AttrR(Int())
    b: AttrRW = AttrRW(Int())


class ChildController(Controller):
    c: AttrW = AttrW(Int())

    @command()
    async def d(self):
        pass


class InitialValuesController(Controller):
    int = AttrRW(Int(), initial_value=4)
    float = AttrRW(Float(), initial_value=3.1)
    bool = AttrRW(Bool(), initial_value=True)
    enum = AttrRW(Enum(InitialEnum), initial_value=InitialEnum.B)
    str = AttrRW(String(), initial_value="initial")
    waveform = AttrRW(
        Waveform(np.int64, shape=(10,)),
        initial_value=np.array(range(10), dtype=np.int64),
    )


def run(pv_prefix="SOFTIOC_TEST_DEVICE"):
    controller = ParentController()
    controller.child = ChildController()
    fastcs = FastCS(
        controller, [EpicsCATransport(ca_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))]
    )
    fastcs.run(interactive=False)


def run_initial_value(pv_prefix="SOFTIOC_INITIAL_DEVICE"):
    epics_options = EpicsCAOptions(ca_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))
    controller = InitialValuesController()
    fastcs = FastCS(controller, [epics_options])
    fastcs.run()


if __name__ == "__main__":
    run()
