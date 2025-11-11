from pathlib import Path

from fastcs.attributes import AttrR
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsGUIOptions, EpicsIOCOptions


class TemperatureController(Controller):
    device_id = AttrR(String())

    def __init__(self, settings: IPConnectionSettings):
        super().__init__()

        self._ip_settings = settings
        self._connection = IPConnection()

    async def connect(self):
        await self._connection.connect(self._ip_settings)


gui_options = EpicsGUIOptions(
    output_path=Path(".") / "demo.bob", title="Demo Temperature Controller"
)
epics_ca = EpicsCATransport(gui=gui_options, epicsca=EpicsIOCOptions(pv_prefix="DEMO"))
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(connection_settings), [epics_ca])


if __name__ == "__main__":
    fastcs.run()
