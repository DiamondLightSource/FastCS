import asyncio
from abc import ABC, abstractmethod
from typing import Any

from fastcs.controller_api import ControllerAPI


class Transport(ABC):
    """A base class for transport's implementation
    so it can be used in FastCS."""

    @property
    @abstractmethod
    def options(self) -> Any:
        pass

    @abstractmethod
    async def serve(self) -> None:
        pass

    @abstractmethod
    def create_docs(self) -> None:
        pass

    @abstractmethod
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
