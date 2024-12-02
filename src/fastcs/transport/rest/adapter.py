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
        self._options = options or RestOptions()
        self._server = RestServer(controller)

    @property
    def options(self) -> RestOptions:
        return self._options

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    async def serve(self) -> None:
        await self._server.serve(self.options.rest)
