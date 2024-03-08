import asyncio

from dataclasses import dataclass
from typing import Optional

from pymodbus.client.base import ModbusBaseClient
from pymodbus.client import (
    AsyncModbusSerialClient,
    AsyncModbusTcpClient,
    AsyncModbusUdpClient,
)
from pymodbus.exceptions import ModbusException

from pymodbus.framer import Framer
from pymodbus.pdu import ExceptionResponse


# Constants
CR = "\r"
TIMEOUT = 1.0  # Seconds
RECV_BUFFER = 4096  # Bytes


@dataclass
class ModbusConnectionSettings:
    host: str = "127.0.0.1"
    port: int = 7001
    slave: int = 0

class ModbusConnection:

    def __init__(self, settings: ModbusConnectionSettings) -> None:

        self.host, self.port, self.slave = settings.host, settings.port, settings.slave
        self.running: bool = False

        self._client: ModbusBaseClient

    async def connect(self, framer=Framer.SOCKET):
        raise NotImplementedError


    def disconnect(self):
        self._client.close()

    async def _read(self, address: int, count: int = 2) -> Optional[str]:
        # address -= 1  # modbus spec starts from 0 not 1
        try:
            # address_hex = hex(address)
            rr = await self._client.read_holding_registers(address, count=count, slave=self.slave)  # type: ignore
            print(f"Response: {rr}")
        except ModbusException as exc:  # pragma no cover
            # Received ModbusException from library
            self.disconnect()
            return
        if rr.isError():  # pragma no cover
            # Received Modbus library error
            self.disconnect()
            return
        if isinstance(rr, ExceptionResponse):  # pragma no cover
            # Received Modbus library exception
            # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
            self.disconnect()

    async def send(self, address: int, value: int) -> None:
        """Send a request.

        Args:
        address: The register address to write to.
        value: The value to write.
        """
        await self._client.write_registers(address, value, slave=self.slave)
        resp = await self._read(address, 2)

class ModbusSerialConnection(ModbusConnection):

    def __init__(self, settings: ModbusConnectionSettings) -> None:
        super().__init__(settings)

    async def connect(self, framer=Framer.SOCKET):
        self._client: AsyncModbusSerialClient = AsyncModbusSerialClient(
            str(self.port),
            framer=framer,
            timeout=10,
            retries=3,
            retry_on_empty=False,
            close_comm_on_error=False,
            strict=True,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
        )

        await self._client.connect()
        assert self._client.connected

class ModbusTcpConnection(ModbusConnection):

    def __init__(self, settings: ModbusConnectionSettings) -> None:
        super().__init__(settings)

    async def connect(self, framer=Framer.SOCKET):
        self._client: AsyncModbusTcpClient = AsyncModbusTcpClient(
            self.host,
            self.port,
            framer=framer,
            timeout=10,
            retries=3,
            retry_on_empty=False,
            close_comm_on_error=False,
            strict=True,
            source_address=("localhost", 0),
        )

        await self._client.connect()
        assert self._client.connected

class ModbusUdpConnection(ModbusConnection):

    def __init__(self, settings: ModbusConnectionSettings) -> None:
        super().__init__(settings)

    async def connect(self, framer=Framer.SOCKET):
        self._client: AsyncModbusUdpClient = AsyncModbusUdpClient(
            self.host,
            self.port,
            framer=framer,
            timeout=10,
            retries=3,
            retry_on_empty=False,
            close_comm_on_error=False,
            strict=True,
            source_address=("localhost", 0),
        )

        await self._client.connect()
        assert self._client.connected