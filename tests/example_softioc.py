from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Int
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.wrappers import command


class ParentController(Controller):
    a: AttrR = AttrR(Int())
    b: AttrRW = AttrRW(Int())


class ChildController(Controller):
    c: AttrW = AttrW(Int())

    @command()
    async def d(self):
        pass


def run(pv_prefix="SOFTIOC_TEST_DEVICE"):
    controller = ParentController()
    controller.child = ChildController()
    fastcs = FastCS(
        controller, [EpicsCATransport(ca_ioc=EpicsIOCOptions(pv_prefix=pv_prefix))]
    )
    fastcs.run()


if __name__ == "__main__":
    run()
