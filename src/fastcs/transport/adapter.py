from abc import ABC, abstractmethod


class TransportAdapter(ABC):
    @abstractmethod
    def run(self) -> None:
        pass

    @abstractmethod
    def create_docs(self) -> None:
        pass

    @abstractmethod
    def create_gui(self) -> None:
        pass
