from fastcs.attributes import AttrR
from fastcs.controllers import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transports.epics import EpicsIOCOptions
from fastcs.transports.epics.ca.transport import EpicsCATransport


class TemperatureController(Controller):
    device_id = AttrR(String())


epics_ca = EpicsCATransport(epicsca=EpicsIOCOptions(pv_prefix="DEMO"))
fastcs = FastCS(TemperatureController(), [epics_ca])

if __name__ == "__main__":
    fastcs.run()
