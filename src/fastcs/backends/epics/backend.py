from fastcs.backend import Backend
from fastcs.controller import Controller

from .docs import EpicsDocs, EpicsDocsOptions
from .gui import EpicsGUI, EpicsGUIOptions
from .ioc import EpicsIOC, EpicsIOCOptions


class EpicsBackend(Backend):
    def __init__(self, controller: Controller, pv_prefix: str = "MY-DEVICE-PREFIX"):
        super().__init__(controller)

        self._pv_prefix = pv_prefix
        self._ioc = EpicsIOC(pv_prefix, self._mapping)

    def create_docs(self, options: EpicsDocsOptions | None = None) -> None:
        EpicsDocs(self._mapping).create_docs(options)

    def create_gui(self, options: EpicsGUIOptions | None = None) -> None:
        EpicsGUI(self._mapping, self._pv_prefix).create_gui(options)

    def _run(self, options: EpicsIOCOptions | None = None):
        self._ioc.run(self._dispatcher, self._context, options)
