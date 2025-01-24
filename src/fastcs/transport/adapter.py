from abc import ABC, abstractmethod
from typing import Any


class TransportAdapter(ABC):
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
