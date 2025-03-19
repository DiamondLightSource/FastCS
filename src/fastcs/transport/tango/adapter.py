import asyncio

from fastcs.controller_api import ControllerAPI
from fastcs.transport.adapter import TransportAdapter

from .dsr import TangoDSR
from .options import TangoOptions


class TangoTransport(TransportAdapter):
    """Tango transport."""

    def __init__(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
        options: TangoOptions | None = None,
    ):
        self._options = options or TangoOptions()
        self._dsr = TangoDSR(controller_api, loop)

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
