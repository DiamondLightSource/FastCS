import asyncio

from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter
from fastcs.transport.epics.ca.ioc import EpicsCAIOC
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import EpicsGUI


class EpicsCATransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop,
        options: EpicsCAOptions | None = None,
    ) -> None:
        self._controller = controller
        self._loop = loop
        self._options = options or EpicsCAOptions()
        self._pv_prefix = self.options.ioc.pv_prefix
        self._ioc = EpicsCAIOC(
            self.options.ioc.pv_prefix,
            controller,
            self._options.ioc,
        )

    @property
    def options(self) -> EpicsCAOptions:
        return self._options

    def create_docs(self) -> None:
        EpicsDocs(self._controller).create_docs(self.options.docs)

    def create_gui(self) -> None:
        EpicsGUI(self._controller, self._pv_prefix).create_gui(self.options.gui)

    async def serve(self) -> None:
        print(f"Running FastCS IOC: {self._pv_prefix}")
        self._ioc.run(self._loop)
        while True:
            await asyncio.sleep(1)
