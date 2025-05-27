from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Float, String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions


@dataclass
class TemperatureControllerHandler(AttrHandlerRW):
    command_name: str
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
        response = await self.controller.connection.send_query(
            f"{self.command_name}?\r\n"
        )
        value = response.strip("\r\n")

        await attr.set(attr.dtype(value))

    async def put(self, attr: AttrW, value: Any):
        await self.controller.connection.send_command(
            f"{self.command_name}={value}\r\n"
        )


class TemperatureController(Controller):
    device_id = AttrR(String(), handler=TemperatureControllerHandler("ID"))
    power = AttrR(Float(), handler=TemperatureControllerHandler("P"))
    ramp_rate = AttrRW(Float(), handler=TemperatureControllerHandler("R"))

    def __init__(self, settings: IPConnectionSettings):
        super().__init__()

        self._ip_settings = settings
        self.connection = IPConnection()

    async def connect(self):
        await self.connection.connect(self._ip_settings)


epics_options = EpicsCAOptions(ca_ioc=EpicsIOCOptions(pv_prefix="DEMO"))
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(connection_settings), [epics_options])

# fastcs.run()  # Commented as this will block
