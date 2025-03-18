from fastcs.controller_api import ControllerAPI

from .options import EpicsDocsOptions


class EpicsDocs:
    """For creating docs in the EPICS transports."""

    def __init__(self, controller_apis: ControllerAPI) -> None:
        self._controller_apis = controller_apis

    def create_docs(self, options: EpicsDocsOptions | None = None) -> None:
        if options is None:
            options = EpicsDocsOptions()
