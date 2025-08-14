from fastcs.controller import Controller
from fastcs.launch import FastCS


class TemperatureController(Controller):
    pass


fastcs = FastCS(TemperatureController(), [])
# fastcs.run() # Commented as this will block
