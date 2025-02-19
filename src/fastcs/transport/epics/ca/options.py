from dataclasses import dataclass, field

from ..options import (
    EpicsDocsOptions,
    EpicsGUIOptions,
    EpicsIOCOptions,
)


@dataclass
class EpicsCAOptions:
    docs: EpicsDocsOptions = field(default_factory=EpicsDocsOptions)
    gui: EpicsGUIOptions = field(default_factory=EpicsGUIOptions)
    ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
