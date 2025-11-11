import asyncio
from dataclasses import dataclass, field

from fastcs.controller_api import ControllerAPI
from fastcs.transport.transport import Transport

from .dsr import TangoDSR, TangoDSROptions


@dataclass
class TangoTransport(Transport):
    """Tango transport."""

    tango: TangoDSROptions = field(default_factory=TangoDSROptions)

    def connect(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ):
        self._dsr = TangoDSR(controller_api, loop)

    async def serve(self) -> None:
        coro = asyncio.to_thread(self._dsr.run, self.tango)
        await coro
