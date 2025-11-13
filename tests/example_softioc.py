from pathlib import Path

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller, ControllerVector
from fastcs.datatypes import Int
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport, EpicsGUIOptions
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
    first_controller = ParentController()
    second_controller = ChildController()
    vector = ControllerVector({i: ChildController() for i in range(2)})
    first_controller.add_sub_controller("ChildVector", vector)
    gui_options = EpicsGUIOptions(
        output_path=Path(".") / "demo.bob", title="Demo Vector"
    )
    fastcs = FastCS(
        [first_controller, second_controller],
        [
            EpicsCATransport(
                epicsca=EpicsIOCOptions(pv_prefixes=[pv_prefix, f"{pv_prefix}_2"]),
                gui=gui_options,
            )
        ],
    )
    fastcs.run(interactive=True)


if __name__ == "__main__":
    run()
