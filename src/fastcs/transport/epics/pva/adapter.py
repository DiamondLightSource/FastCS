from fastcs.attributes import Attribute, AttrR, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.transport.adapter import TransportAdapter
from fastcs.transport.epics.docs import EpicsDocs
from fastcs.transport.epics.gui import PvaEpicsGUI
from fastcs.transport.epics.pva.options import EpicsPVAOptions
from fastcs.util import pascal_to_snake, snake_to_pascal

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

    def print_pvs(self) -> None:
        def _parse_attributes(api: ControllerAPI) -> list:
            prefix = ":".join([self._pv_prefix] + list(api.path))
            attrs = [
                f"{prefix}:{snake_to_pascal(attribute)}"
                for attribute in api.attributes.keys()
            ]
            for sub_api in api.sub_apis.values():
                attrs.extend(_parse_attributes(sub_api))
            return attrs

        print(*_parse_attributes(self._controller_api), sep="\n")

    def _find_pv(self, pv: str) -> Attribute | None:
        pv_path = pv.split(":")
        api_path = pv_path[1:-1]
        attr = pv_path[-1]

        def _filter_attributes(api: ControllerAPI):
            if api.path == api_path:
                return api.attributes.get(pascal_to_snake(attr))
            for sub_api in api.sub_apis.values():
                attribute = _filter_attributes(sub_api)
                if attribute is not None:
                    return attribute
            return None

        return _filter_attributes(self._controller_api)

    async def set_pv(self, pv: str, value) -> None:
        attribute = self._find_pv(pv)
        assert isinstance(attribute, AttrW)
        await attribute.sender.put(attribute, value)

    async def read_pv(self, pv: str) -> None:
        attribute = self._find_pv(pv)
        assert isinstance(attribute, AttrR)
        print(f"{pv}: {attribute.get()}")

    def context(self) -> dict:
        return {
            "print_pvs": self.print_pvs,
            "set_pv": self.set_pv,
            "read_pv": self.read_pv,
        }
