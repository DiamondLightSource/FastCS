import asyncio

from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import EpicsGUI
from fastcs.transport.epics.options import EpicsOptions
from fastcs.transport.epics.softioc.ioc import EpicsIOC


class EpicsTransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop,
        options: EpicsOptions | None = None,
    ) -> None:
        self._controller = controller
        self._loop = loop
        self._options = options or EpicsOptions()
        self._pv_prefix = self.options.ioc.pv_prefix
        self._ioc = EpicsIOC(
            self.options.ioc.pv_prefix,
            controller,
            self._options.ioc,
        )

    @property
    def options(self) -> EpicsOptions:
        return self._options

    def create_docs(self) -> None:
        EpicsDocs(self._controller).create_docs(self.options.docs)

    def create_gui(self) -> None:
        EpicsGUI(self._controller, self._pv_prefix).create_gui(self.options.gui)

    async def serve(self) -> None:
        self._ioc.run(self._loop)
        while True:
            await asyncio.sleep(1)
