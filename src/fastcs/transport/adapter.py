from abc import ABC, abstractmethod
from typing import TypeAlias

from .epics.options import EpicsOptions
from .rest.options import RestOptions
from .tango.options import TangoOptions

# Define a type alias for transport options
TransportOptions: TypeAlias = EpicsOptions | TangoOptions | RestOptions


class TransportAdapter(ABC):
    @property
    @abstractmethod
    def options(self) -> TransportOptions:
        pass

    @abstractmethod
    def run(self) -> None:
        pass

    @abstractmethod
    def create_docs(self) -> None:
        pass

    @abstractmethod
    def create_gui(self) -> None:
        pass
