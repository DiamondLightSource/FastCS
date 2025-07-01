from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastcs.attributes import AttrHandlerR, AttrR
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsGUIOptions, EpicsIOCOptions


@dataclass
class IDUpdater(AttrHandlerR):
    update_period: float | None = 0.2
    _controller: TemperatureController | None = None

    async def initialise(self, controller: BaseController):
        assert isinstance(controller, TemperatureController)
        self._controller = controller

    @property
    def controller(self) -> TemperatureController:
        if self._controller is None:
            raise RuntimeError("Handler not initialised")

        return self._controller

    async def update(self, attr: AttrR):
        response = await self.controller.connection.send_query("ID?\r\n")
        value = response.strip("\r\n")

        await attr.set(value)


class TemperatureController(Controller):
    device_id = AttrR(String(), handler=IDUpdater())

    def __init__(self, settings: IPConnectionSettings):
        super().__init__()

        self._ip_settings = settings
        self.connection = IPConnection()

    async def connect(self):
        await self.connection.connect(self._ip_settings)


gui_options = EpicsGUIOptions(
    output_path=Path(".") / "demo.bob", title="Demo Temperature Controller"
)
epics_options = EpicsCAOptions(
    gui=gui_options,
    ca_ioc=EpicsIOCOptions(pv_prefix="DEMO"),
)
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(connection_settings), [epics_options])

fastcs.create_gui()

# fastcs.run()  # Commented as this will block
