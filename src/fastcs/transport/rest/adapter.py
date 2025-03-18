from fastcs.controller_api import ControllerAPI
from fastcs.transport.adapter import TransportAdapter

from .options import RestOptions
from .rest import RestServer


class RestTransport(TransportAdapter):
    """Rest Transport Adapter."""

    def __init__(
        self,
        controller_api: ControllerAPI,
        options: RestOptions | None = None,
    ):
        self._options = options or RestOptions()
        self._server = RestServer(controller_api)

    @property
    def options(self) -> RestOptions:
        return self._options

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    async def serve(self) -> None:
        await self._server.serve(self.options.rest)
