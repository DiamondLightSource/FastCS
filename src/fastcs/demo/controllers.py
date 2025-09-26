from __future__ import annotations

import asyncio
import enum
import json
from dataclasses import dataclass

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Enum, Float, Int, T
from fastcs.wrappers import command, scan


class OnOffEnum(enum.StrEnum):
    Off = "0"
    On = "1"


@dataclass
class TemperatureControllerSettings:
    num_ramp_controllers: int
    ip_settings: IPConnectionSettings


@dataclass(kw_only=True)
class TemperatureControllerAttributeIORef(AttributeIORef):
    name: str
    update_period: float | None = 0.2


class TemperatureControllerAttributeIO(
    AttributeIO[TemperatureControllerAttributeIORef, T]
):
    def __init__(self, connection: IPConnection, suffix: str):
        self._connection = connection
        self.suffix = suffix

    async def send(
        self, attr: AttrW, ref: TemperatureControllerAttributeIORef, value: T
    ) -> None:
        await self._connection.send_command(
            f"{ref.name}{self.suffix}={attr.dtype(value)}\r\n"
        )

    async def update(
        self, attr: AttrR, ref: TemperatureControllerAttributeIORef
    ) -> None:
        response = await self._connection.send_query(f"{ref.name}{self.suffix}?\r\n")
        response = response.strip("\r\n")

        await attr.set(attr.dtype(response))


class TemperatureController(Controller):
    ramp_rate = AttrRW(Float(), io_ref=TemperatureControllerAttributeIORef(name="R"))
    power = AttrR(Float(), io_ref=TemperatureControllerAttributeIORef(name="P"))

    def __init__(self, settings: TemperatureControllerSettings) -> None:
        self.connection = IPConnection()
        self.suffix = ""
        super().__init__(
            ios=[TemperatureControllerAttributeIO(self.connection, self.suffix)]
        )

        self._settings = settings

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


class TemperatureRampController(Controller):
    start = AttrRW(Int(), io_ref=TemperatureControllerAttributeIORef(name="S"))
    end = AttrRW(Int(), io_ref=TemperatureControllerAttributeIORef(name="E"))
    enabled = AttrRW(
        Enum(OnOffEnum), io_ref=TemperatureControllerAttributeIORef(name="N")
    )
    target = AttrR(Float(prec=3), io_ref=TemperatureControllerAttributeIORef(name="T"))
    actual = AttrR(Float(prec=3), io_ref=TemperatureControllerAttributeIORef(name="A"))
    voltage = AttrR(Float(prec=3))

    def __init__(self, index: int, conn: IPConnection) -> None:
        suffix = f"{index:02d}"
        super().__init__(
            f"Ramp{suffix}", ios=[TemperatureControllerAttributeIO(conn, suffix)]
        )
        self.connection = conn
