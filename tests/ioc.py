from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.backends.epics.backend import EpicsBackend
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Int
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
    controller = ParentController()
    controller.register_sub_controller("Child", ChildController())

    backend = EpicsBackend(controller, "DEVICE")
    backend.run()


if __name__ == "__main__":
    run()
