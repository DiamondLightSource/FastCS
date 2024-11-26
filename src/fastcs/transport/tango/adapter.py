from fastcs.mapping import Mapping
from fastcs.transport.adapter import TransportAdapter

from .dsr import TangoDSR
from .options import TangoOptions


class TangoTransport(TransportAdapter):
    def __init__(
        self,
        mapping: Mapping,
        options: TangoOptions | None = None,
    ):
        self.options = options or TangoOptions()
        self._mapping = mapping
        self._dsr = TangoDSR(self._mapping)

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        self._dsr.run(self.options.dsr)
