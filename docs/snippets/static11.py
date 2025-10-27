import enum
from dataclasses import KW_ONLY, dataclass
from pathlib import Path
from typing import TypeVar

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import Controller
from fastcs.datatypes import Enum, Float, Int, String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsGUIOptions, EpicsIOCOptions

NumberT = TypeVar("NumberT", int, float)


@dataclass
class TemperatureControllerAttributeIORef(AttributeIORef):
    name: str
    _: KW_ONLY
    update_period: float | None = 0.2


class TemperatureControllerAttributeIO(
    AttributeIO[NumberT, TemperatureControllerAttributeIORef]
):
    def __init__(self, connection: IPConnection, suffix: str = ""):
        super().__init__()

        self._connection = connection
        self._suffix = suffix

    async def update(self, attr: AttrR[NumberT, TemperatureControllerAttributeIORef]):
        query = f"{attr.io_ref.name}{self._suffix}?"
        response = await self._connection.send_query(f"{query}\r\n")
        value = response.strip("\r\n")

        await attr.update(attr.dtype(value))

    async def send(
        self, attr: AttrW[NumberT, TemperatureControllerAttributeIORef], value: NumberT
    ) -> None:
        command = f"{attr.io_ref.name}{self._suffix}={attr.dtype(value)}"
        await self._connection.send_command(f"{command}\r\n")


class OnOffEnum(enum.StrEnum):
    Off = "0"
    On = "1"


class TemperatureRampController(Controller):
    start = AttrRW(Int(), io_ref=TemperatureControllerAttributeIORef(name="S"))
    end = AttrRW(Int(), io_ref=TemperatureControllerAttributeIORef(name="E"))
    enabled = AttrRW(Enum(OnOffEnum), io_ref=TemperatureControllerAttributeIORef("N"))

    def __init__(self, index: int, connection: IPConnection) -> None:
        suffix = f"{index:02d}"
        super().__init__(
            f"Ramp{suffix}", ios=[TemperatureControllerAttributeIO(connection, suffix)]
        )


class TemperatureController(Controller):
    device_id = AttrR(String(), io_ref=TemperatureControllerAttributeIORef("ID"))
    power = AttrR(Float(), io_ref=TemperatureControllerAttributeIORef("P"))
    ramp_rate = AttrRW(Float(), io_ref=TemperatureControllerAttributeIORef("R"))

    def __init__(self, ramp_count: int, settings: IPConnectionSettings):
        self._ip_settings = settings
        self._connection = IPConnection()

        super().__init__(ios=[TemperatureControllerAttributeIO(self._connection)])

        self._ramp_controllers: list[TemperatureRampController] = []
        for index in range(1, ramp_count + 1):
            controller = TemperatureRampController(index, self._connection)
            self._ramp_controllers.append(controller)
            self.add_sub_controller(f"R{index}", controller)

    async def connect(self):
        await self._connection.connect(self._ip_settings)


gui_options = EpicsGUIOptions(
    output_path=Path(".") / "demo.bob", title="Demo Temperature Controller"
)
epics_ca = EpicsCATransport(gui=gui_options, ca_ioc=EpicsIOCOptions(pv_prefix="DEMO"))
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(4, connection_settings), [epics_ca])

fastcs.create_gui()

if __name__ == "__main__":
    fastcs.run()
