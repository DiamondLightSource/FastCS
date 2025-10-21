from pathlib import Path

from fastcs.attributes import AttrR
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsGUIOptions
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsIOCOptions


class TemperatureController(Controller):
    device_id = AttrR(String())


gui_options = EpicsGUIOptions(
    output_path=Path(".") / "demo.bob", title="Demo Temperature Controller"
)
epics_ca = EpicsCATransport(gui=gui_options, ca_ioc=EpicsIOCOptions(pv_prefix="DEMO"))
fastcs = FastCS(TemperatureController(), [epics_ca])

fastcs.create_gui()

if __name__ == "__main__":
    fastcs.run()
