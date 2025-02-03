from fastcs.controller import Controller
from fastcs.transport.adapter import TransportAdapter

from .ioc import P4PIOC
from .options import P4POptions


class P4PTransport(TransportAdapter):
    def __init__(
        self,
        controller: Controller,
        options: P4POptions | None = None,
    ) -> None:
        self._controller = controller
        self._options = options or P4POptions()
        self._pv_prefix = self.options.ioc.pv_prefix
        self._ioc = P4PIOC(self.options.ioc.pv_prefix, controller)

    @property
    def options(self) -> P4POptions:
        return self._options

    async def serve(self) -> None:
        await self._ioc.run()

    def create_docs(self) -> None:
        raise NotImplementedError

    def create_gui(self) -> None:
        raise NotImplementedError
