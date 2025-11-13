import asyncio
from dataclasses import dataclass, field

from fastcs.controller_api import ControllerAPI
from fastcs.logging import logger as _fastcs_logger
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import PvaEpicsGUI
from fastcs.transport.epics.options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)
from fastcs.transport.transport import Transport

from .ioc import P4PIOC

logger = _fastcs_logger.bind(logger_name=__name__)


@dataclass
class EpicsPVATransport(Transport):
    """PV access transport."""

    epicspva: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
    docs: EpicsDocsOptions | None = None
    gui: EpicsGUIOptions | None = None

    def connect(
        self,
        controller_apis: list[ControllerAPI],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._controller_api = controller_apis
        self._pv_prefix = self.epicspva.pv_prefixes
        self._ioc = P4PIOC(self.epicspva.pv_prefixes, controller_apis)

        for pv_prefix, api in zip(self._pv_prefix, controller_apis, strict=True):
            if self.docs is not None:
                EpicsDocs(api).create_docs(self.docs)

            if self.gui is not None:
                PvaEpicsGUI(api, pv_prefix).create_gui(self.gui)

    async def serve(self) -> None:
        logger.info("Running IOC", pv_prefix=self._pv_prefix)
        await self._ioc.run()

    def __repr__(self):
        return f"EpicsPVATransport({self._pv_prefix})"
