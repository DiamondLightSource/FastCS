import asyncio
from dataclasses import dataclass, field
from typing import Any

from softioc import softioc

from fastcs.logging import bind_logger
from fastcs.transports.controller_api import ControllerAPI
from fastcs.transports.epics import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)
from fastcs.transports.epics.ca.ioc import EpicsCAIOC
from fastcs.transports.epics.docs import EpicsDocs
from fastcs.transports.epics.gui import EpicsGUI
from fastcs.transports.transport import Transport

logger = bind_logger(logger_name=__name__)


@dataclass
class EpicsCATransport(Transport):
    """Channel access transport."""

    epicsca: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
    docs: EpicsDocsOptions | None = None
    gui: EpicsGUIOptions | None = None

    def connect(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._controller_api = controller_api
        self._loop = loop
        self._pv_prefix = self.epicsca.pv_prefix
        self._ioc = EpicsCAIOC(self.epicsca.pv_prefix, controller_api, self.epicsca)

        if self.docs is not None:
            EpicsDocs(self._controller_api).create_docs(self.docs)

        if self.gui is not None:
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

    def __repr__(self):
        return f"EpicsCATransport({self._pv_prefix})"
