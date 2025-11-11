from fastcs.attributes import AttrR
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsIOCOptions


class TemperatureController(Controller):
    device_id = AttrR(String())


epics_ca = EpicsCATransport(epicsca=EpicsIOCOptions(pv_prefix="DEMO"))
fastcs = FastCS(TemperatureController(), [epics_ca])

if __name__ == "__main__":
    fastcs.run()
