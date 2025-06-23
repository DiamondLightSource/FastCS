from fastcs.attributes import AttrR
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions


class TemperatureController(Controller):
    device_id = AttrR(String())


epics_options = EpicsCAOptions(ca_ioc=EpicsIOCOptions(pv_prefix="DEMO"))
fastcs = FastCS(TemperatureController(), [epics_options])

# fastcs.run()  # Commented as this will block
