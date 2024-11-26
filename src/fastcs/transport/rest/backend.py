from fastcs.backend import Backend
from fastcs.controller import Controller

from .rest import RestServer


class RestBackend(Backend):
    def __init__(self, controller: Controller):
        super().__init__(controller)

        self._server = RestServer(self._mapping)

    def _run(self):
        self._server.run()
