import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Union

from fastcs.controller_api import ControllerAPI


@dataclass
class Transport:
    """A base class for transport's implementation
    so it can be used in FastCS."""

    subclasses: ClassVar[list[type["Transport"]]] = []

    def __init_subclass__(cls):
        cls.subclasses.append(cls)

    @classmethod
    def union(cls):
        if not cls.subclasses:
            raise RuntimeError("No Transports found")

        return Union[tuple(cls.subclasses)]  # noqa: UP007

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
