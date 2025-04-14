from dataclasses import dataclass

from fastcs.attributes import AttrR, Updater
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions


@dataclass
class IDUpdater(Updater):
    update_period: float | None = 0.2

    async def update(self, controller: BaseController, attr: AttrR):
        assert isinstance(controller, TemperatureController)

        response = await controller.connection.send_query("ID?\r\n")
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


epics_options = EpicsCAOptions(ioc=EpicsIOCOptions(pv_prefix="DEMO"))
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(connection_settings), [epics_options])

# fastcs.run()  # Commented as this will block
