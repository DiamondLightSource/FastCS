from fastcs.controller_api import ControllerAPI
from fastcs.transport.adapter import TransportAdapter
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import PvaEpicsGUI
from fastcs.transport.epics.pva.options import EpicsPVAOptions
from fastcs.util import snake_to_pascal

from .ioc import P4PIOC


class EpicsPVATransport(TransportAdapter):
    """PV access transport."""

    def __init__(
        self,
        controller_api: ControllerAPI,
        options: EpicsPVAOptions | None = None,
    ) -> None:
        self._controller_api = controller_api
        self._options = options or EpicsPVAOptions()
        self._pv_prefix = self.options.pva_ioc.pv_prefix
        self._ioc = P4PIOC(self.options.pva_ioc.pv_prefix, controller_api)

    @property
    def options(self) -> EpicsPVAOptions:
        return self._options

    async def serve(self) -> None:
        print(f"Running FastCS IOC: {self._pv_prefix}")
        await self._ioc.run()

    def create_docs(self) -> None:
        EpicsDocs(self._controller_api).create_docs(self.options.docs)

    def create_gui(self) -> None:
        PvaEpicsGUI(self._controller_api, self._pv_prefix).create_gui(self.options.gui)

    def print_all(self) -> None:
        def parse_attributes(api: ControllerAPI) -> list:
            prefix = ":".join([self._pv_prefix] + list(api.path))
            attrs = [
                f"{prefix}:{snake_to_pascal(attribute)}"
                for attribute in api.attributes.keys()
            ]
            for sub_api in api.sub_apis.values():
                attrs.extend(parse_attributes(sub_api))
            return attrs

        print(*parse_attributes(self._controller_api), sep="\n")

    def context(self) -> dict:
        return {"print_all": self.print_all}
