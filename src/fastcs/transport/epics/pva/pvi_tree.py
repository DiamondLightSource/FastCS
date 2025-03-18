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
class _PviSignalInfo:
    """For storing a pv and it's access in pvi parsing."""

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


class PviDevice(dict[str, "PviDevice"]):
    """For creating a pvi structure in pva."""

    pv_prefix: str
    description: str | None
    device_signal_info: _PviSignalInfo | None

    def __init__(
        self,
        pv_prefix: str,
        description: str | None = None,
        device_signal_info: _PviSignalInfo | None = None,
    ):
        self.pv_prefix = pv_prefix
        self.description = description
        self.device_signal_info = device_signal_info

    def __missing__(self, key: str) -> "PviDevice":
        new_device = PviDevice(pv_prefix=f"{self.pv_prefix}:{key}")
        self[key] = new_device
        return self[key]

    def get_recursively(self, *args: str) -> "PviDevice":
        d = self
        for arg in args:
            d = d[arg]
        return d

    def _get_signal_infos(self) -> dict[str, _PviSignalInfo]:
        device_signal_infos: dict[str, _PviSignalInfo] = {}

        for sub_device_name, sub_device in self.items():
            if sub_device:
                device_signal_infos[f"{sub_device_name}:PVI"] = _PviSignalInfo(
                    pv=f"{sub_device.pv_prefix}:PVI", access="d"
                )
            if sub_device.device_signal_info:
                device_signal_infos[sub_device_name] = sub_device.device_signal_info

        return device_signal_infos

    def _make_p4p_raw_value(self) -> dict:
        p4p_raw_value = defaultdict(dict)
        for pv_leaf, signal_info in self._get_signal_infos().items():
            stripped_leaf = pv_leaf.rstrip(":PVI")
            is_controller = stripped_leaf != pv_leaf
            pvi_name, number = _pv_to_pvi_name(stripped_leaf or pv_leaf)
            if is_controller and number is not None:
                if signal_info.access not in p4p_raw_value[pvi_name]:
                    p4p_raw_value[pvi_name][signal_info.access] = {}
                p4p_raw_value[pvi_name][signal_info.access][f"v{number}"] = (
                    signal_info.pv
                )
            elif is_controller:
                p4p_raw_value[pvi_name][signal_info.access] = signal_info.pv
            else:
                attr_pvi_name = f"{pvi_name}{'' if number is None else number}"
                p4p_raw_value[attr_pvi_name][signal_info.access] = signal_info.pv

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

        for sub_device in self.values():
            if sub_device:
                sub_device.make_provider(provider=provider)

        return provider


# TODO: This can be dramatically cleaned up after https://github.com/DiamondLightSource/FastCS/issues/122
class PviTree:
    """For storing pvi structures."""

    def __init__(self, pv_prefix: str):
        self._pvi_tree_root: PviDevice = PviDevice(pv_prefix)

    def add_sub_device(
        self,
        device_pv: str,
        description: str | None,
    ):
        if ":" not in device_pv:
            assert device_pv == self._pvi_tree_root.pv_prefix
            self._pvi_tree_root.description = description
        else:
            self._pvi_tree_root.get_recursively(
                *device_pv.split(":")[1:]  # To remove the prefix
            ).description = description

    def add_signal(
        self,
        attribute_pv: str,
        access: AccessModeType,
    ):
        leaf_device = self._pvi_tree_root.get_recursively(*attribute_pv.split(":")[1:])

        if leaf_device.device_signal_info is not None:
            raise ValueError(f"Tried to add the field '{attribute_pv}' twice.")

        leaf_device.device_signal_info = _PviSignalInfo(pv=attribute_pv, access=access)

    def make_provider(self) -> StaticProvider:
        return self._pvi_tree_root.make_provider()
