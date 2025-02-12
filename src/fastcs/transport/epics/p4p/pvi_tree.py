import re
from dataclasses import dataclass
from typing import Literal

from p4p import Type, Value
from p4p.nt.common import alarm, timeStamp
from p4p.server import StaticProvider
from p4p.server.asyncio import SharedPV

from fastcs.controller import BaseController

from .types import p4p_alarm_states, p4p_timestamp_now

AccessModeType = Literal["r", "w", "rw", "d", "x"]

PviName = str


@dataclass
class _PviFieldInfo:
    pv: str
    access: AccessModeType

    # Controller type to check all pvi "d" in a group are the same type.
    controller_t: type[BaseController] | None

    # Number for the int value on the end of the pv,
    # corresponding to `v<number>` in the structure.
    number: int | None = None


@dataclass
class _PviBlockInfo:
    field_infos: dict[str, list[_PviFieldInfo]]
    description: str | None


def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _pv_to_pvi_field(pv: str) -> tuple[str, int | None]:
    leaf = pv.rsplit(":", maxsplit=1)[-1]
    match = re.search(r"(\d+)$", leaf)
    number = int(match.group(1)) if match else None
    string_without_number = re.sub(r"\d+$", "", leaf)
    return _camel_to_snake(string_without_number), number


# TODO: This can be dramatically cleaned up after https://github.com/DiamondLightSource/FastCS/issues/122


class PviTree:
    def __init__(self):
        self._pvi_info: dict[PviName, _PviBlockInfo] = {}

    def add_block(
        self,
        block_pv: str,
        description: str | None,
        controller_t: type[BaseController] | None = None,
    ):
        pvi_name, number = _pv_to_pvi_field(block_pv)
        if block_pv not in self._pvi_info:
            self._pvi_info[block_pv] = _PviBlockInfo(
                field_infos={}, description=description
            )

        parent_block_pv = block_pv.rsplit(":", maxsplit=1)[0]

        if parent_block_pv == block_pv:
            return

        if pvi_name not in self._pvi_info[parent_block_pv].field_infos:
            self._pvi_info[parent_block_pv].field_infos[pvi_name] = []
        elif (
            controller_t
            is not (
                other_field := self._pvi_info[parent_block_pv].field_infos[pvi_name][-1]
            ).controller_t
        ):
            raise ValueError(
                f"Can't add `{block_pv}` to pvi group {pvi_name}. "
                f"It represents a {controller_t}, however {other_field.pv} "
                f"represents a {other_field.controller_t}."
            )

        self._pvi_info[parent_block_pv].field_infos[pvi_name].append(
            _PviFieldInfo(
                pv=f"{block_pv}:PVI",
                access="d",
                controller_t=controller_t,
                number=number,
            )
        )

    def add_field(
        self,
        attribute_pv: str,
        access: AccessModeType,
    ):
        pvi_name, number = _pv_to_pvi_field(attribute_pv)
        parent_block_pv = attribute_pv.rsplit(":", maxsplit=1)[0]

        if pvi_name not in self._pvi_info[parent_block_pv].field_infos:
            self._pvi_info[parent_block_pv].field_infos[pvi_name] = []

        self._pvi_info[parent_block_pv].field_infos[pvi_name].append(
            _PviFieldInfo(
                pv=attribute_pv, access=access, controller_t=None, number=number
            )
        )

    def make_provider(self) -> StaticProvider:
        provider = StaticProvider("PVI")

        for block_pv, block_info in self._pvi_info.items():
            provider.add(
                f"{block_pv}:PVI",
                SharedPV(initial=self._p4p_value(block_info)),
            )
        return provider

    def _p4p_value(self, block_info: _PviBlockInfo) -> Value:
        pvi_structure = []
        for pvi_name, field_infos in block_info.field_infos.items():
            if len(field_infos) == 1:
                field_datatype = [(field_infos[0].access, "s")]
            else:
                assert all(
                    field_info.access == field_infos[0].access
                    for field_info in field_infos
                )
                field_datatype = [
                    (
                        field_infos[0].access,
                        (
                            "S",
                            None,
                            [
                                (f"v{field_info.number}", "s")
                                for field_info in field_infos
                            ],
                        ),
                    )
                ]

            substructure = (
                pvi_name,
                (
                    "S",
                    "structure",
                    # If there are multiple field_infos then they ar the same type of
                    # controller.
                    field_datatype,
                ),
            )
            pvi_structure.append(substructure)

        p4p_type = Type(
            [
                ("alarm", alarm),
                ("timeStamp", timeStamp),
                ("display", ("S", None, [("description", "s")])),
                ("value", ("S", "structure", tuple(pvi_structure))),
            ]
        )

        value = {}
        for pvi_name, field_infos in block_info.field_infos.items():
            if len(field_infos) == 1:
                value[pvi_name] = {field_infos[0].access: field_infos[0].pv}
            else:
                value[pvi_name] = {
                    field_infos[0].access: {
                        f"v{field_info.number}": field_info.pv
                        for field_info in field_infos
                    }
                }

        # Done here so the value can be (none) if block_info.description isn't defined.
        display = (
            {"display": {"description": block_info.description}}
            if block_info.description
            else {}
        )

        return Value(
            p4p_type,
            {
                **p4p_alarm_states(),
                **p4p_timestamp_now(),
                **display,
                "value": value,
            },
        )
