from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass
class EpicsDocsOptions:
    path: Path = Path(".")
    depth: int | None = None


class EpicsGUIFormat(Enum):
    bob = ".bob"
    edl = ".edl"


@dataclass
class EpicsGUIOptions:
    output_path: Path = Path(".") / "output.bob"
    file_format: EpicsGUIFormat = EpicsGUIFormat.bob
    title: str = "Simple Device"


@dataclass
class EpicsIOCOptions:
    pv_prefix: str = "MY-DEVICE-PREFIX"
