from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter

from .options import RestOptions
from .rest import RestServer


class RestTransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        options: RestOptions | None = None,
    ):
        self.options = options or RestOptions()
        self._server = RestServer(controller)

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        self._server.run(self.options.rest)
