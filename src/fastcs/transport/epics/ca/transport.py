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

    epicsca: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
    docs: EpicsDocsOptions | None = None
    gui: EpicsGUIOptions | None = None

    def connect(  # type: ignore
        self,
        controller_apis: list[ControllerAPI],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._controller_apis = controller_apis
        self._loop = loop
        self._pv_prefixes = self.epicsca.pv_prefixes
        self._ioc = EpicsCAIOC(self.epicsca.pv_prefixes, controller_apis, self.epicsca)

        for pv_prefix, api in zip(self._pv_prefixes, controller_apis, strict=True):
            if self.docs is not None:
                EpicsDocs(api).create_docs(self.docs)

            if self.gui is not None:
                EpicsGUI(api, pv_prefix).create_gui(self.gui)

    async def serve(self) -> None:
        logger.info("Running IOC", pv_prefix=self._pv_prefixes)
        self._ioc.run(self._loop)

    @property
    def context(self) -> dict[str, Any]:
        return {
            command_name: getattr(softioc, command_name)
            for command_name in softioc.command_names
            if command_name != "exit"
        }

    def __repr__(self):
        return f"EpicsCATransport({self._pv_prefixes})"
