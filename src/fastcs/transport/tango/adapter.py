import asyncio

from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter

from .dsr import TangoDSR
from .options import TangoOptions


class TangoTransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop,
        options: TangoOptions | None = None,
    ):
        self._options = options or TangoOptions()
        self._dsr = TangoDSR(controller, loop)

    @property
    def options(self) -> TangoOptions:
        return self._options

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    async def serve(self) -> None:
        coro = asyncio.to_thread(
            self._dsr.run,
            self.options.dsr,
        )
        await coro
