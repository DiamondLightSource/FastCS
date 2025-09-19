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

    docs: EpicsDocsOptions = field(default_factory=EpicsDocsOptions)
    gui: EpicsGUIOptions = field(default_factory=EpicsGUIOptions)
    pva_ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)

    def initialise(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._controller_api = controller_api
        self._pv_prefix = self.pva_ioc.pv_prefix
        self._ioc = P4PIOC(self.pva_ioc.pv_prefix, controller_api)

    async def serve(self) -> None:
        logger.info("Running IOC", pv_prefix=self._pv_prefix)
        await self._ioc.run()

    def create_docs(self) -> None:
        EpicsDocs(self._controller_api).create_docs(self.docs)

    def create_gui(self) -> None:
        PvaEpicsGUI(self._controller_api, self._pv_prefix).create_gui(self.gui)
