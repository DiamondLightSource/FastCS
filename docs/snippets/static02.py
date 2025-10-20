from fastcs.controller import Controller
from fastcs.launch import FastCS


class TemperatureController(Controller):
    pass


fastcs = FastCS(TemperatureController(), [])

if __name__ == "__main__":
    fastcs.run()
