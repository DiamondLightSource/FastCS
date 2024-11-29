from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@dataclass
class EpicsDocsOptions:
    path: Path = Path.cwd()
    depth: int | None = None


class EpicsGUIFormat(Enum):
    bob = ".bob"
    edl = ".edl"


@dataclass
class EpicsGUIOptions:
    output_path: Path = Path.cwd() / "output.bob"
    file_format: EpicsGUIFormat = EpicsGUIFormat.bob
    title: str = "Simple Device"


@dataclass
class EpicsIOCOptions:
    terminal: bool = True
    pv_prefix: str = "MY-DEVICE-PREFIX"


@dataclass
class EpicsOptions:
    docs: EpicsDocsOptions = field(default_factory=EpicsDocsOptions)
    gui: EpicsGUIOptions = field(default_factory=EpicsGUIOptions)
    ioc: EpicsIOCOptions = field(default_factory=EpicsIOCOptions)
