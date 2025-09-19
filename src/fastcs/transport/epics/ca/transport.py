import asyncio
from dataclasses import dataclass, field
from typing import Any

from softioc import softioc

from fastcs.controller_api import ControllerAPI
from fastcs.logging import logger as _fastcs_logger
from fastcs.transport.epics.ca.ioc import EpicsCAIOC
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import EpicsGUI
from fastcs.transport.epics.options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)
from fastcs.transport.transport import Transport

logger = _fastcs_logger.bind(logger_name=__name__)


@dataclass
class EpicsCATransport(Transport):
    """Channel access transport."""

    docs: EpicsDocsOptions = field(default_factory=EpicsDocsOptions)
    gui: EpicsGUIOptions = field(default_factory=EpicsGUIOptions)
    ca_ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)

    def initialise(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._controller_api = controller_api
        self._loop = loop
        self._pv_prefix = self.ca_ioc.pv_prefix
        self._ioc = EpicsCAIOC(self.ca_ioc.pv_prefix, controller_api, self.ca_ioc)

    def create_docs(self) -> None:
        EpicsDocs(self._controller_api).create_docs(self.docs)

    def create_gui(self) -> None:
        EpicsGUI(self._controller_api, self._pv_prefix).create_gui(self.gui)

    async def serve(self) -> None:
        logger.info("Running IOC", pv_prefix=self._pv_prefix)
        self._ioc.run(self._loop)

    @property
    def context(self) -> dict[str, Any]:
        return {
            command_name: getattr(softioc, command_name)
            for command_name in softioc.command_names
            if command_name != "exit"
        }
