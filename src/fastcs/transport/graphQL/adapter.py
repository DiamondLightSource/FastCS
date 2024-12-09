from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter

from .graphQL import GraphQLServer
from .options import GraphQLOptions


class GraphQLTransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        options: GraphQLOptions | None = None,
    ):
        self.options = options or GraphQLOptions()
        self._server = GraphQLServer(controller)

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        self._server.run(self.options.gql)
