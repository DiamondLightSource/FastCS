from dataclasses import dataclass
from pathlib import Path

from fastcs.mapping import Mapping


@dataclass
class EpicsDocsOptions:
    path: Path = Path.cwd()
    depth: int | None = None


class EpicsDocs:
    def __init__(self, mapping: Mapping) -> None:
        self._mapping = mapping

    def create_docs(self, options: EpicsDocsOptions | None = None) -> None:
        if options is None:
            options = EpicsDocsOptions()
