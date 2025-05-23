from dataclasses import dataclass, field

from fastcs.transport.epics.options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)


@dataclass
class EpicsPVAOptions:
    """Options for the EPICS PVA transport."""

    docs: EpicsDocsOptions = field(default_factory=EpicsDocsOptions)
    gui: EpicsGUIOptions = field(default_factory=EpicsGUIOptions)
    pva_ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
