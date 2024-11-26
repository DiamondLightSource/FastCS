from fastcs.mapping import Mapping
from fastcs.transport.adapter import TransportAdapter

from .options import RestOptions
from .rest import RestServer


class RestTransport(TransportAdapter):
    def __init__(
        self,
        mapping: Mapping,
        options: RestOptions | None = None,
    ):
        self.options = options or RestOptions()
        self._mapping = mapping
        self._server = RestServer(self._mapping)

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        self._server.run(self.options.rest)
