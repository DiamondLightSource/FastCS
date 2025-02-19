from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import EpicsGUI
from fastcs.transport.epics.pva.options import EpicsPVAOptions

from .ioc import P4PIOC


class EpicsPVATransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        options: EpicsPVAOptions | None = None,
    ) -> None:
        self._controller = controller
        self._options = options or EpicsPVAOptions()
        self._pv_prefix = self.options.ioc.pv_prefix
        self._ioc = P4PIOC(self.options.ioc.pv_prefix, controller)

    @property
    def options(self) -> EpicsPVAOptions:
        return self._options

    async def serve(self) -> None:
        print(f"Running FastCS IOC: {self._pv_prefix}")
        await self._ioc.run()

    def create_docs(self) -> None:
        EpicsDocs(self._controller).create_docs(self.options.docs)

    def create_gui(self) -> None:
        EpicsGUI(self._controller, self._pv_prefix).create_gui(self.options.gui)
