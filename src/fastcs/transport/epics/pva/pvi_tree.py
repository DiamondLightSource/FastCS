import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from p4p import Type, Value
from p4p.nt.common import alarm, timeStamp
from p4p.server import StaticProvider
from p4p.server.asyncio import SharedPV

from .types import p4p_alarm_states, p4p_timestamp_now

AccessModeType = Literal["r", "w", "rw", "d", "x"]

PviName = str


@dataclass
class _PviFieldInfo:
    pv: str
    access: AccessModeType


def _pascal_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _pv_to_pvi_name(pv: str) -> tuple[str, int | None]:
    leaf = pv.rsplit(":", maxsplit=1)[-1]
    match = re.search(r"(\d+)$", leaf)
    number = int(match.group(1)) if match else None
    string_without_number = re.sub(r"\d+$", "", leaf)
    return _pascal_to_snake(string_without_number), number


class PviBlock(dict[str, "PviBlock"]):
    pv_prefix: str
    description: str | None
    block_field_info: _PviFieldInfo | None

    def __init__(
        self,
        pv_prefix: str,
        description: str | None = None,
        block_field_info: _PviFieldInfo | None = None,
    ):
        self.pv_prefix = pv_prefix
        self.description = description
        self.block_field_info = block_field_info

    def __missing__(self, key: str) -> "PviBlock":
        new_block = PviBlock(pv_prefix=f"{self.pv_prefix}:{key}")
        self[key] = new_block
        return self[key]

    def get_recursively(self, *args: str) -> "PviBlock":
        d = self
        for arg in args:
            d = d[arg]
        return d

    def _get_field_infos(self) -> dict[str, _PviFieldInfo]:
        block_field_infos: dict[str, _PviFieldInfo] = {}

        for sub_block_name, sub_block in self.items():
            if sub_block:
                block_field_infos[f"{sub_block_name}:PVI"] = _PviFieldInfo(
                    pv=f"{sub_block.pv_prefix}:PVI", access="d"
                )
            if sub_block.block_field_info:
                block_field_infos[sub_block_name] = sub_block.block_field_info

        return block_field_infos

    def _make_p4p_raw_value(self) -> dict:
        p4p_raw_value = defaultdict(dict)
        for pv_leaf, field_info in self._get_field_infos().items():
            pvi_name, number = _pv_to_pvi_name(pv_leaf.rstrip(":PVI") or pv_leaf)
            if number is not None:
                if field_info.access not in p4p_raw_value[pvi_name]:
                    p4p_raw_value[pvi_name][field_info.access] = {}
                p4p_raw_value[pvi_name][field_info.access][f"v{number}"] = field_info.pv
            else:
                p4p_raw_value[pvi_name][field_info.access] = field_info.pv

        return p4p_raw_value

    def _make_type_for_raw_value(self, raw_value: dict) -> Type:
        p4p_raw_type = []
        for pvi_group_name, access_to_field in raw_value.items():
            pvi_group_structure = []
            for access, field in access_to_field.items():
                if isinstance(field, str):
                    pvi_group_structure.append((access, "s"))
                elif isinstance(field, dict):
                    pvi_group_structure.append(
                        (
                            access,
                            (
                                "S",
                                None,
                                [(v, "s") for v, _ in field.items()],
                            ),
                        )
                    )

            p4p_raw_type.append(
                (pvi_group_name, ("S", "structure", pvi_group_structure))
            )

        return Type(
            [
                ("alarm", alarm),
                ("timeStamp", timeStamp),
                ("display", ("S", None, [("description", "s")])),
                ("value", ("S", "structure", p4p_raw_type)),
            ]
        )

    def make_p4p_value(self) -> Value:
        display = (
            {"display": {"description": self.description}}
            if self.description is not None
            else {}
        )  # Defined here so the value can be (none)

        raw_value = self._make_p4p_raw_value()
        p4p_type = self._make_type_for_raw_value(raw_value)

        return Value(
            p4p_type,
            {
                **p4p_alarm_states(),
                **p4p_timestamp_now(),
                **display,
                "value": raw_value,
            },
        )

    def make_provider(
        self,
        provider: StaticProvider | None = None,
    ) -> StaticProvider:
        if provider is None:
            provider = StaticProvider("PVI")

        provider.add(
            f"{self.pv_prefix}:PVI",
            SharedPV(initial=self.make_p4p_value()),
        )

        for sub_block in self.values():
            if sub_block:
                sub_block.make_provider(provider=provider)

        return provider


# TODO: This can be dramatically cleaned up after https://github.com/DiamondLightSource/FastCS/issues/122
class PviTree:
    def __init__(self, pv_prefix: str):
        self._pvi_tree_root: PviBlock = PviBlock(pv_prefix)

    def add_block(
        self,
        block_pv: str,
        description: str | None,
    ):
        if ":" not in block_pv:
            assert block_pv == self._pvi_tree_root.pv_prefix
            self._pvi_tree_root.description = description
        else:
            self._pvi_tree_root.get_recursively(
                *block_pv.split(":")[1:]  # To remove the prefix
            ).description = description

    def add_field(
        self,
        attribute_pv: str,
        access: AccessModeType,
    ):
        leaf_block = self._pvi_tree_root.get_recursively(*attribute_pv.split(":")[1:])

        if leaf_block.block_field_info is not None:
            raise ValueError(f"Tried to add the field '{attribute_pv}' twice.")

        leaf_block.block_field_info = _PviFieldInfo(pv=attribute_pv, access=access)

    def make_provider(self) -> StaticProvider:
        return self._pvi_tree_root.make_provider()
