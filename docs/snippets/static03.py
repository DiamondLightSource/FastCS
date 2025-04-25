from fastcs.attributes import AttrR
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS


class TemperatureController(Controller):
    device_id = AttrR(String())


fastcs = FastCS(TemperatureController(), [])
fastcs.run()
