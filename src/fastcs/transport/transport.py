import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from fastcs.controller_api import ControllerAPI


@dataclass
class Transport:
    """A base class for transport's implementation
    so it can be used in FastCS."""

    @abstractmethod
    async def serve(self) -> None:
        pass

    def create_docs(self) -> None:
        pass

    def create_gui(self) -> None:
        pass

    @property
    def context(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def initialise(
        self,
        controller_api: ControllerAPI,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        pass
