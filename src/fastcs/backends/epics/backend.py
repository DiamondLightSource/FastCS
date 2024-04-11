from fastcs.mapping import Mapping

from .docs import EpicsDocs, EpicsDocsOptions
from .gui import EpicsGUI, EpicsGUIOptions
from .ioc import EpicsIOC


class EpicsBackend:
    def __init__(self, mapping: Mapping, pv_prefix: str = "MY-DEVICE-PREFIX"):
        self._mapping = mapping
        self._pv_prefix = pv_prefix

    def create_docs(self, options: EpicsDocsOptions | None = None) -> None:
        docs = EpicsDocs(self._mapping)
        docs.create_docs(options)

    def create_gui(self, options: EpicsGUIOptions | None = None) -> None:
        gui = EpicsGUI(self._mapping, self._pv_prefix)
        gui.create_gui(options)

    def get_ioc(self) -> EpicsIOC:
        return EpicsIOC(self._mapping, self._pv_prefix)
