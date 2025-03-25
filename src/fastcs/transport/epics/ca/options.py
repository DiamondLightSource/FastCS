from dataclasses import dataclass, field

from ..options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)


@dataclass
class EpicsCAOptions:
    """Options for the EPICS CA transport."""

    docs: EpicsDocsOptions | None = None
    gui: EpicsGUIOptions | None = None
    ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
