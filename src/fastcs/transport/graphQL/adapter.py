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
        self._options = options or GraphQLOptions()
        self._server = GraphQLServer(controller)

    @property
    def options(self) -> GraphQLOptions:
        return self._options

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    async def serve(self) -> None:
        await self._server.serve(self.options.gql)
