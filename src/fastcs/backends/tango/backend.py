from fastcs.mapping import Mapping

from .dsr import TangoDSR


class TangoBackend:
    def __init__(self, mapping: Mapping):
        self._mapping = mapping

    def get_dsr(self) -> TangoDSR:
        return TangoDSR(self._mapping)
