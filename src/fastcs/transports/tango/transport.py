import asyncio
from dataclasses import dataclass, field

from fastcs.controllers import ControllerAPI
from fastcs.transports.transport import Transport

from .dsr import TangoDSR, TangoDSROptions


@dataclass
class TangoTransport(Transport):
    """Tango transport."""

    tango: TangoDSROptions = field(default_factory=TangoDSROptions)

    def connect(self, controller_api: ControllerAPI):
        self._dsr = TangoDSR(controller_api, asyncio.get_running_loop())

    async def serve(self) -> None:
        await asyncio.to_thread(self._dsr.run, self.tango)
