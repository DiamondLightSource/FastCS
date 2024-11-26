from fastcs.controller import Controller

from .options import EpicsDocsOptions


class EpicsDocs:
    def __init__(self, controller: Controller) -> None:
        self._controller = controller

    def create_docs(self, options: EpicsDocsOptions | None = None) -> None:
        if options is None:
            options = EpicsDocsOptions()
