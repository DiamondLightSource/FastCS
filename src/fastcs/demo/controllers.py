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
class TempControllerSettings:
    num_ramp_controllers: int
    ip_settings: IPConnectionSettings


@dataclass
class TempControllerHandler(AttrHandlerRW):
    name: str
    update_period: float | None = 0.2
    _controller: TempController | TempRampController | None = None

    async def initialise(self, controller: BaseController):
        assert isinstance(controller, TempController | TempRampController)
        self._controller = controller

    @property
    def controller(self) -> TempController | TempRampController:
        if self._controller is None:
            raise RuntimeError("Handler not initialised")

        return self._controller

    async def put(self, attr: AttrW, value: Any) -> None:
        await self.controller.conn.send_command(
            f"{self.name}{self.controller.suffix}={attr.dtype(value)}\r\n"
        )

    async def update(self, attr: AttrR) -> None:
        response = await self.controller.conn.send_query(
            f"{self.name}{self.controller.suffix}?\r\n"
        )
        response = response.strip("\r\n")

        await attr.set(attr.dtype(response))


class TempController(Controller):
    ramp_rate = AttrRW(Float(), handler=TempControllerHandler("R"))
    power = AttrR(Float(), handler=TempControllerHandler("P"))

    def __init__(self, settings: TempControllerSettings) -> None:
        super().__init__()

        self.suffix = ""
        self._settings = settings
        self.conn = IPConnection()

        self._ramp_controllers: list[TempRampController] = []
        for index in range(1, settings.num_ramp_controllers + 1):
            controller = TempRampController(index, self.conn)
            self._ramp_controllers.append(controller)
            self.register_sub_controller(f"R{index}", controller)

    @command()
    async def cancel_all(self) -> None:
        for rc in self._ramp_controllers:
            await rc.enabled.process(OnOffEnum.Off)
            # TODO: The requests all get concatenated and the sim doesn't handle it
            await asyncio.sleep(0.1)

    async def connect(self) -> None:
        await self.conn.connect(self._settings.ip_settings)

    async def close(self) -> None:
        await self.conn.close()

    @scan(0.1)
    async def update_voltages(self):
        voltages = json.loads((await self.conn.send_query("V?\r\n")).strip("\r\n"))
        for index, controller in enumerate(self._ramp_controllers):
            await controller.voltage.set(float(voltages[index]))


class TempRampController(SubController):
    start = AttrRW(Int(), handler=TempControllerHandler("S"))
    end = AttrRW(Int(), handler=TempControllerHandler("E"))
    enabled = AttrRW(Enum(OnOffEnum), handler=TempControllerHandler("N"))
    target = AttrR(Float(prec=3), handler=TempControllerHandler("T"))
    actual = AttrR(Float(prec=3), handler=TempControllerHandler("A"))
    voltage = AttrR(Float(prec=3))

    def __init__(self, index: int, conn: IPConnection) -> None:
        self.suffix = f"{index:02d}"
        super().__init__(f"Ramp{self.suffix}")
        self.conn = conn
