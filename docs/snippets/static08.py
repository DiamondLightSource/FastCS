from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrR, AttrRW, AttrW, Handler
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Float, String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions


@dataclass
class TemperatureControllerHandler(Handler):
    command_name: str
    update_period: float | None = 0.2

    async def update(self, controller: BaseController, attr: AttrR):
        assert isinstance(controller, TemperatureController)

        response = await controller.connection.send_query(f"{self.command_name}?\r\n")
        value = response.strip("\r\n")

        await attr.set(attr.dtype(value))

    async def put(self, controller: BaseController, attr: AttrW, value: Any):
        assert isinstance(controller, TemperatureController)

        await controller.connection.send_command(f"{self.command_name}={value}\r\n")


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


epics_options = EpicsCAOptions(ioc=EpicsIOCOptions(pv_prefix="DEMO"))
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(connection_settings), [epics_options])

# fastcs.run()  # Commented as this will block
