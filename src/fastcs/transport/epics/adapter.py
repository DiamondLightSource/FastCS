from softioc.asyncio_dispatcher import AsyncioDispatcher

from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter

from .docs import EpicsDocs
from .gui import EpicsGUI
from .ioc import EpicsIOC
from .options import EpicsOptions


class EpicsTransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        dispatcher: AsyncioDispatcher,
        options: EpicsOptions | None = None,
    ) -> None:
        self.options = options or EpicsOptions()
        self._controller = controller
        self._dispatcher = dispatcher
        self._pv_prefix = self.options.ioc.pv_prefix
        self._ioc = EpicsIOC(self.options.ioc.pv_prefix, controller)

    def create_docs(self) -> None:
        EpicsDocs(self._controller).create_docs(self.options.docs)

    def create_gui(self) -> None:
        EpicsGUI(self._controller, self._pv_prefix).create_gui(self.options.gui)

    def run(self):
        self._ioc.run(self._dispatcher)
