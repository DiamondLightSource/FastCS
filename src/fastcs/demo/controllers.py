from __future__ import annotations

import asyncio
import enum
import json
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller, SubController
from fastcs.datatypes import Enum, Float, Int
from fastcs.wrappers import command, scan


class OnOffEnum(enum.StrEnum):
    Off = "0"
    On = "1"


@dataclass
class TemperatureControllerSettings:
    num_ramp_controllers: int
    ip_settings: IPConnectionSettings


@dataclass
class TemperatureControllerHandler(AttrHandlerRW):
    name: str
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

    async def put(self, attr: AttrW, value: Any) -> None:
        await self.controller.connection.send_command(
            f"{self.name}{self.controller.suffix}={attr.dtype(value)}\r\n"
        )

    async def update(self, attr: AttrR) -> None:
        response = await self.controller.connection.send_query(
            f"{self.name}{self.controller.suffix}?\r\n"
        )
        response = response.strip("\r\n")

        await attr.set(attr.dtype(response))


class TemperatureController(Controller):
    ramp_rate = AttrRW(Float(), handler=TemperatureControllerHandler("R"))
    power = AttrR(Float(), handler=TemperatureControllerHandler("P"))

    def __init__(self, settings: TemperatureControllerSettings) -> None:
        super().__init__()

        self.suffix = ""
        self._settings = settings
        self.connection = IPConnection()

        self._ramp_controllers: list[TemperatureRampController] = []
        for index in range(1, settings.num_ramp_controllers + 1):
            controller = TemperatureRampController(index, self.connection)
            self._ramp_controllers.append(controller)
            self.register_sub_controller(f"R{index}", controller)

    @command()
    async def cancel_all(self) -> None:
        for rc in self._ramp_controllers:
            await rc.enabled.process(OnOffEnum.Off)
            # TODO: The requests all get concatenated and the sim doesn't handle it
            await asyncio.sleep(0.1)

    async def connect(self) -> None:
        await self.connection.connect(self._settings.ip_settings)

    async def close(self) -> None:
        await self.connection.close()

    @scan(0.1)
    async def update_voltages(self):
        voltages = json.loads(
            (await self.connection.send_query("V?\r\n")).strip("\r\n")
        )
        for index, controller in enumerate(self._ramp_controllers):
            await controller.voltage.set(float(voltages[index]))


class TemperatureRampController(SubController):
    start = AttrRW(Int(), handler=TemperatureControllerHandler("S"))
    end = AttrRW(Int(), handler=TemperatureControllerHandler("E"))
    enabled = AttrRW(Enum(OnOffEnum), handler=TemperatureControllerHandler("N"))
    target = AttrR(Float(prec=3), handler=TemperatureControllerHandler("T"))
    actual = AttrR(Float(prec=3), handler=TemperatureControllerHandler("A"))
    voltage = AttrR(Float(prec=3))

    def __init__(self, index: int, conn: IPConnection) -> None:
        self.suffix = f"{index:02d}"
        super().__init__(f"Ramp{self.suffix}")
        self.connection = conn
