from dataclasses import dataclass, field

from fastcs.transport.epics.options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)


@dataclass
class EpicsPVAOptions:
    """Options for the EPICS PVA transport."""

    docs: EpicsDocsOptions | None = None
    gui: EpicsGUIOptions | None = None
    ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
