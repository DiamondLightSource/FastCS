import asyncio

from fastcs.controller_api import ControllerAPI
from fastcs.transport import Transport

from .graphql import GraphQLServer
from .options import GraphQLOptions


class GraphQLTransport(Transport):
    """GraphQL transport."""

    def __init__(self, options: GraphQLOptions | None = None):
        self._options = options or GraphQLOptions()

    def initialise(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self._server = GraphQLServer(controller_api)

    @property
    def options(self) -> GraphQLOptions:
        return self._options

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    async def serve(self) -> None:
        await self._server.serve(self.options.gql)
