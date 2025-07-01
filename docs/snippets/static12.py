from __future__ import annotations

import enum
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller, SubController
from fastcs.datatypes import Enum, Float, Int, String
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsGUIOptions, EpicsIOCOptions
from fastcs.wrappers import scan


@dataclass
class TemperatureControllerHandler(AttrHandlerRW):
    command_name: str
    update_period: float | None = 0.2
    _controller: TemperatureController | TemperatureRampController | None = None

    async def initialise(self, controller: BaseController):
        assert isinstance(controller, TemperatureController | TemperatureRampController)
        self._controller = controller

    @property
    def controller(self) -> TemperatureController | TemperatureRampController:
        if self._controller is None:
            raise RuntimeError("Handler not initialised")

        return self._controller

    async def update(self, attr: AttrR):
        response = await self.controller.connection.send_query(
            f"{self.command_name}{self.controller.suffix}?\r\n"
        )
        value = response.strip("\r\n")

        await attr.set(attr.dtype(value))

    async def put(self, attr: AttrW, value: Any):
        await self.controller.connection.send_command(
            f"{self.command_name}{self.controller.suffix}={attr.dtype(value)}\r\n"
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


gui_options = EpicsGUIOptions(
    output_path=Path(".") / "demo.bob", title="Demo Temperature Controller"
)
epics_options = EpicsCAOptions(
    gui=gui_options,
    ca_ioc=EpicsIOCOptions(pv_prefix="DEMO"),
)
connection_settings = IPConnectionSettings("localhost", 25565)
fastcs = FastCS(TemperatureController(4, connection_settings), [epics_options])

fastcs.create_gui()

# fastcs.run()  # Commented as this will block
