import asyncio
from dataclasses import dataclass, field

from fastcs.controller_api import ControllerAPI
from fastcs.transport.transport import Transport

from .options import RestServerOptions
from .rest import RestServer


@dataclass
class RestTransport(Transport):
    """Rest Transport Adapter."""

    rest: RestServerOptions = field(default_factory=RestServerOptions)

    def connect(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ):
        self._server = RestServer(controller_api)

    async def serve(self) -> None:
        await self._server.serve(self.rest)

    def __repr__(self) -> str:
        return f"RestTransport({self.rest.host}:{self.rest.port})"
