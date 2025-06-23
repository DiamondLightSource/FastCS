from pathlib import Path

from fastcs.attributes import AttrR
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsGUIOptions, EpicsIOCOptions


class TemperatureController(Controller):
    device_id = AttrR(String())

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
