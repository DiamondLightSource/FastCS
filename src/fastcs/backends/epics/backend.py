from fastcs.backend import Backend
from fastcs.controller import Controller

from .docs import EpicsDocs, EpicsDocsOptions
from .gui import EpicsGUI, EpicsGUIOptions
from .ioc import EpicsIOC, EpicsIOCOptions


class EpicsBackend(Backend):
    def __init__(
        self,
        controller: Controller,
        pv_prefix: str = "MY-DEVICE-PREFIX",
        ioc_options: EpicsIOCOptions | None = None,
    ):
        super().__init__(controller)

        self._pv_prefix = pv_prefix
        self.ioc_options = ioc_options or EpicsIOCOptions()
        self._ioc = EpicsIOC(pv_prefix, self._mapping, options=ioc_options)

    def create_docs(self, docs_options: EpicsDocsOptions | None = None) -> None:
        EpicsDocs(self._mapping).create_docs(docs_options)

    def create_gui(self, gui_options: EpicsGUIOptions | None = None) -> None:
        assert self.ioc_options.name_options is not None
        EpicsGUI(
            self._mapping, self._pv_prefix, self.ioc_options.name_options
        ).create_gui(gui_options)

    def _run(self):
        self._ioc.run(self._dispatcher, self._context)
