import asyncio
from dataclasses import dataclass, field

from fastcs.controller_api import ControllerAPI
from fastcs.transport.transport import Transport

from .graphql import GraphQLServer
from .options import GraphQLServerOptions


@dataclass
class GraphQLTransport(Transport):
    """GraphQL transport."""

    graphql: GraphQLServerOptions = field(default_factory=GraphQLServerOptions)

    def connect(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ):
        self._server = GraphQLServer(controller_api)

    async def serve(self) -> None:
        await self._server.serve(self.graphql)

    def __repr__(self) -> str:
        return f"GraphQLTransport({self.graphql.host}:{self.graphql.port})"
