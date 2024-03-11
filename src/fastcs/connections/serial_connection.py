import asyncio
import socket
import warnings
from dataclasses import dataclass
from typing import Optional, Tuple

# Constants
TIMEOUT = 1.0  # Seconds
RECV_BUFFER = 4096  # Bytes


@dataclass
class SerialConnectionSettings:
    ip: str = "127.0.0.1"
    port: int = 7001


class SerialConnection:
    def __init__(self) -> None:
        # self._endpoint: Tuple[str, int] =
        self._socket: socket.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )
        self._socket.settimeout(TIMEOUT)
        self._lock = asyncio.Lock()

    def connect(self, settings: SerialConnectionSettings):
        self._endpoint: Tuple[str, int] = (settings.ip, settings.port)
        self._socket.connect(self._endpoint)
        # Clear initial connection messages
        # TODO: Are these useful? Use as confirmation of connection?
        # self._clear_socket()
        self.clear_socket()

    def disconnect(self):
        self._socket.close()

    def clear_socket(self):
        """Read from socket until we timeout"""
        while True:
            try:
                self._socket.recv(RECV_BUFFER)
            except socket.timeout:
                break

    @staticmethod
    def _format_message(message: bytes) -> bytes:
        """Format message for printing by appending a newline char.

        Args:
            message: The message to format.

        Returns:
            The formatted message.
        """
        return message + b"\n"

    def _send(self, request: bytes):
        """Send a request.

        Args:
            request: The request string to send.
        """
        self._socket.send(self._format_message(request))

    async def _send_receive(self, request: bytes) -> Optional[bytes]:
        """Sends a request and attempts to decode the response.

        Does not determine if the response indicates acknowledgement
        from the device.

        Args:
            request: The request string to send.

        Returns:
            If the response could be decoded,
            then it is returned. Otherwise None is returned.
        """
        async with self._lock:
            self._send(request)

            if request.endswith(b"?"):
                try:
                    response = self._socket.recv(RECV_BUFFER)
                    return response
                except UnicodeDecodeError as e:
                    warnings.warn(f"{e}:\n{self._format_message(response).decode()}")
                except socket.timeout:
                    warnings.warn("Didn't receive a response in time.")

        return None

    async def send_receive(self, request: bytes) -> Optional[bytes]:
        """Sends a request and attempts to decode the response.

        Args:
            request: The request string to send.

        Returns:
            The decoded response string if the
            request was successful, otherwise None is returned.
        """

        response = await self._send_receive(request)
        if response is None:
            return None

        return response
