from dataclasses import dataclass, field

from ..options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)


@dataclass
class EpicsCAOptions:
    """Options for the EPICS CA transport."""

    docs: EpicsDocsOptions = field(default_factory=EpicsDocsOptions)
    gui: EpicsGUIOptions = field(default_factory=EpicsGUIOptions)
    ca_ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
