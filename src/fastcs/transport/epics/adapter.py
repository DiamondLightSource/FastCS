from typing import cast

from softioc.asyncio_dispatcher import AsyncioDispatcher as Dispatcher

from fastcs.mapping import Mapping
from fastcs.transport.adapter import TransportAdapter
from fastcs.util import AsyncioDispatcher

from .docs import EpicsDocs
from .gui import EpicsGUI
from .ioc import EpicsIOC
from .options import EpicsOptions


class EpicsTransport(TransportAdapter):
    def __init__(
        self,
        mapping: Mapping,
        context: dict,
        dispatcher: AsyncioDispatcher,
        options: EpicsOptions | None = None,
    ) -> None:
        self.options = options or EpicsOptions()
        self._mapping = mapping
        self._context = context
        self._dispatcher = dispatcher
        self._pv_prefix = self.options.ioc.pv_prefix
        self._ioc = EpicsIOC(self.options.ioc.pv_prefix, self._mapping)

    def create_docs(self) -> None:
        EpicsDocs(self._mapping).create_docs(self.options.docs)

    def create_gui(self) -> None:
        EpicsGUI(self._mapping, self._pv_prefix).create_gui(self.options.gui)

    def run(self):
        self._ioc.run(
            cast(Dispatcher, self._dispatcher),
            self._context,
        )
