from fastcs.backend import Backend
from fastcs.controller import Controller

from .dsr import TangoDSR


class TangoBackend(Backend):
    def __init__(self, controller: Controller):
        super().__init__(controller)

        self._dsr = TangoDSR(self._mapping)

    def _run(self):
        self._dsr.run()
