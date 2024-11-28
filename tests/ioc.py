from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Int
from fastcs.launch import FastCS
from fastcs.transport.epics.options import EpicsIOCOptions, EpicsOptions
from fastcs.wrappers import command


class ParentController(Controller):
    a: AttrR = AttrR(Int())
    b: AttrRW = AttrRW(Int())


class ChildController(SubController):
    c: AttrW = AttrW(Int())

    @command()
    async def d(self):
        pass


def run():
    epics_options = EpicsOptions(ioc=EpicsIOCOptions(pv_prefix="DEVICE"))
    controller = ParentController()
    controller.register_sub_controller("Child", ChildController())
    fastcs = FastCS(controller, epics_options)
    fastcs.run()


if __name__ == "__main__":
    run()
