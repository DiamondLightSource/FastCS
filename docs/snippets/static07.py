from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import Controller
from fastcs.datatypes import String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsGUIOptions, EpicsIOCOptions

NumberT = TypeVar("NumberT", int, float)


@dataclass
class IDAttributeIORef(AttributeIORef):
    update_period: float | None = 0.2


class IDAttributeIO(AttributeIO[NumberT, IDAttributeIORef]):
    def __init__(self, connection: IPConnection):
        super().__init__()

        self._connection = connection

    async def update(self, attr: AttrR[NumberT, IDAttributeIORef]):
        response = await self._connection.send_query("ID?\r\n")
        value = response.strip("\r\n")

        await attr.update(attr.dtype(value))


class TemperatureController(Controller):
    device_id = AttrR(String(), io_ref=IDAttributeIORef())

    def __init__(self, settings: IPConnectionSettings):
        self._ip_settings = settings
        self._connection = IPConnection()

        super().__init__(ios=[IDAttributeIO(self._connection)])

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
