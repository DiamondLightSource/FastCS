from fastcs.mapping import Mapping

from .options import EpicsDocsOptions


class EpicsDocs:
    def __init__(self, mapping: Mapping) -> None:
        self._mapping = mapping

    def create_docs(self, options: EpicsDocsOptions | None = None) -> None:
        if options is None:
            options = EpicsDocsOptions()
