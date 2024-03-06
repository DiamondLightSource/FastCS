"""ZeroMQ adapter for use in a stream device."""

import asyncio
from dataclasses import dataclass
from typing import Iterable, List, Optional

import aiozmq
import zmq


@dataclass
class ZMQConnection:
    """An adapter for a ZeroMQ data stream."""

    zmq_host: str = "127.0.0.1"
    zmq_port: int = 5555
    zmq_type: int = zmq.DEALER
    running: bool = False

    def get_setup(self) -> None:
        """Print out the current configuration."""
        print(
            f"""
Host: {self.zmq_host}
Port: {self.zmq_port}
Type: {self.zmq_type.name}
Running: {self.running}
"""
        )

    async def start_stream(self) -> None:
        """Start the ZeroMQ stream."""
        print("starting stream...")

        self._socket = await aiozmq.create_zmq_stream(
            self.zmq_type, connect=f"tcp://{self.zmq_host}:{self.zmq_port}"
        )  # type: ignore
        if self.zmq_type == zmq.SUB:
            self._socket.transport.setsockopt(zmq.SUBSCRIBE, b"")
        self._socket.transport.setsockopt(zmq.LINGER, 0)

        print(f"Stream started. {self._socket}")

    async def close_stream(self) -> None:
        """Close the ZeroMQ stream."""
        self._socket.close()

        self.running = False

    def send_message(self, message: List[bytes]) -> None:
        """
        Send a message down the ZeroMQ stream.

        Sets up an asyncio task to put the message on the message queue, before
        being processed.

        Args:
            message (str): The message to send down the ZeroMQ stream.
        """
        self._send_message_queue.put_nowait(message)

    async def _read_response(self) -> Optional[bytes]:
        """
        Read and return a response once received on the socket.

        Returns:
            Optional[bytes]: If received, a response is returned, else None
        """
        if self.zmq_type is not zmq.DEALER:
            try:
                resp = await asyncio.wait_for(self._socket.read(), timeout=20)
                return resp[0]
            except asyncio.TimeoutError:
                pass
        else:
            discard = True
            while discard:
                try:
                    multipart_resp = await asyncio.wait_for(
                        self._socket.read(), timeout=20
                    )
                    if multipart_resp[0] == b"":
                        discard = False
                        resp = multipart_resp[1]
                        return resp
                except asyncio.TimeoutError:
                    pass
        return None

    async def get_response(self) -> bytes:
        """
        Get response from the received message queue.

        Returns:
            bytes: Received response message
        """
        return await self._recv_message_queue.get()

    async def run_forever(self) -> None:
        """Run the ZeroMQ adapter continuously."""
        self._send_message_queue: asyncio.Queue = asyncio.Queue()
        self._recv_message_queue: asyncio.Queue = asyncio.Queue()

        try:
            if getattr(self, "_socket", None) is None:
                await self.start_stream()
        except Exception as e:
            print("Exception when starting stream:", e)

        self.running = True

        if self.zmq_type == zmq.DEALER:
            await asyncio.gather(
                *[
                    self._process_message_queue(),
                    self._process_response_queue(),
                ]
            )
        elif self.zmq_type == zmq.SUB:
            await asyncio.gather(
                *[
                    self._process_response_queue(),
                ]
            )

    def check_if_running(self):
        """Return the running state of the adapter."""
        return self.running

    async def _process_message_queue(self) -> None:
        """Process message queue for sending messages over the ZeroMQ stream."""
        print("Processing message queue...")
        running = True
        while running:
            message = await self._send_message_queue.get()
            await self._process_message(message)
            running = self.check_if_running()

    async def _process_message(self, message: Iterable[bytes]) -> None:
        """Process message to send over the ZeroMQ stream.

        Args:
            message (Iterable[bytes]): Message to send over the ZeroMQ stream.
        """
        if message is not None:
            if not self._socket._closing:
                try:
                    if self.zmq_type is not zmq.DEALER:
                        self._socket.write(message)
                    else:
                        self._socket._transport._zmq_sock.send(b"", flags=zmq.SNDMORE)
                        self._socket.write(message)
                except zmq.error.ZMQError as e:
                    print("ZMQ Error", e)
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Error, {e}")
                    print("Unable to write to ZMQ stream, trying again...")
                    await asyncio.sleep(1)
            else:
                print("Socket closed...")
                await asyncio.sleep(5)
        else:
            print("No message")

    async def _process_response_queue(self) -> None:
        """Process response message queue from the ZeroMQ stream."""
        print("Processing response queue...")
        running = True
        while running:
            resp = await self._read_response()
            if resp is None:
                continue
            self._recv_message_queue.put_nowait(resp)
            running = self.check_if_running()
