import asyncio

from fastcs.controller_api import ControllerAPI
from fastcs.transport import Transport

from .dsr import TangoDSR
from .options import TangoOptions


class TangoTransport(Transport):
    """Tango transport."""

    def __init__(self, options: TangoOptions | None = None):
        self._options = options or TangoOptions()

    def initialise(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ):
        if loop is None:
            raise ValueError("TangoTransport expects a non-None loop")
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
