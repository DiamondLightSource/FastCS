import enum
import json
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrR, AttrRW, AttrW, Handler
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller, SubController
from fastcs.datatypes import Enum, Float, Int, String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.wrappers import scan


@dataclass
class TemperatureControllerHandler(Handler):
    command_name: str
    update_period: float | None = 0.2

    async def update(self, controller: BaseController, attr: AttrR):
        assert isinstance(controller, TemperatureController | TemperatureRampController)

        response = await controller.connection.send_query(
            f"{self.command_name}{controller.suffix}?\r\n"
        )
        value = response.strip("\r\n")

        await attr.set(attr.dtype(value))

    async def put(self, controller: BaseController, attr: AttrW, value: Any):
        assert isinstance(controller, TemperatureController | TemperatureRampController)

        await controller.connection.send_command(
            f"{self.command_name}{controller.suffix}={value}\r\n"
        )


class OnOffEnum(enum.StrEnum):
    Off = "0"
    On = "1"


class TemperatureRampController(SubController):
    start = AttrRW(Int(), handler=TemperatureControllerHandler("S"))
    end = AttrRW(Int(), handler=TemperatureControllerHandler("E"))
    enabled = AttrRW(Enum(OnOffEnum), handler=TemperatureControllerHandler("N"))
    target = AttrR(Float(), handler=TemperatureControllerHandler("T"))
    actual = AttrR(Float(), handler=TemperatureControllerHandler("A"))
    voltage = AttrR(Float())

    def __init__(self, index: int, connection: IPConnection):
        self.suffix = f"{index:02d}"

        super().__init__(f"Ramp{self.suffix}")

        self.connection = connection


class TemperatureController(Controller):
    device_id = AttrR(String(), handler=TemperatureControllerHandler("ID"))
    power = AttrR(Float(), handler=TemperatureControllerHandler("P"))
    ramp_rate = AttrRW(Float(), handler=TemperatureControllerHandler("R"))

    suffix = ""

    def __init__(self, ramp_count: int, settings: IPConnectionSettings):
        super().__init__()

        self._ip_settings = settings
        self.connection = IPConnection()

        self._ramp_controllers: list[TemperatureRampController] = []
        for idx in range(1, ramp_count + 1):
            ramp_controller = TemperatureRampController(idx, self.connection)
            self._ramp_controllers.append(ramp_controller)
            self.register_sub_controller(f"R{idx}", ramp_controller)

    async def connect(self):
        await self.connection.connect(self._ip_settings)

    @scan(0.1)
    async def update_voltages(self):
        voltages = json.loads(
            (await self.connection.send_query("V?\r\n")).strip("\r\n")
        )
        for index, controller in enumerate(self._ramp_controllers):
            await controller.voltage.set(float(voltages[index]))


epics_options = EpicsCAOptions(ioc=EpicsIOCOptions(pv_prefix="DEMO"))
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(4, connection_settings), [epics_options])

# fastcs.run()  # Commented as this will block
