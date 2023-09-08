from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pvi._format.base import Formatter
from pvi._yaml_utils import deserialize_yaml
from pvi.device import (
    LED,
    CheckBox,
    Component,
    Device,
    Grid,
    Group,
    ReadWidget,
    SignalR,
    SignalRW,
    SignalW,
    SignalX,
    TextRead,
    TextWrite,
    Tree,
    WriteWidget,
)

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, DataType, Float, Int
from fastcs.exceptions import FastCSException
from fastcs.mapping import Mapping

FORMATTER_YAML = Path.cwd() / ".." / "pvi" / "formatters" / "dls.bob.pvi.formatter.yaml"


class EpicsGUIFormat(Enum):
    bob = ".bob"
    edl = ".edl"


@dataclass
class EpicsGUIOptions:
    output_path: Path = Path.cwd() / "output.bob"
    file_format: EpicsGUIFormat = EpicsGUIFormat.bob


class EpicsGUI:
    def __init__(self, mapping: Mapping) -> None:
        self._mapping = mapping

    @staticmethod
    def _get_pv(attr_path: str, name: str):
        if attr_path:
            attr_path = ":" + attr_path
        attr_path += ":"

        pv = attr_path.upper() + name.title().replace("_", "")

        return pv

    @staticmethod
    def _get_read_widget(datatype: DataType) -> ReadWidget:
        match datatype:
            case Bool():
                return LED()
            case Int() | Float():
                return TextRead()
            case _:
                raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")

    @staticmethod
    def _get_write_widget(datatype: DataType) -> WriteWidget:
        match datatype:
            case Bool():
                return CheckBox()
            case Int() | Float():
                return TextWrite()
            case _:
                raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")

    @classmethod
    def _get_attribute_component(cls, attr_path: str, name: str, attribute: Attribute):
        pv = cls._get_pv(attr_path, name)
        name = name.title().replace("_", " ")

        match attribute:
            case AttrRW():
                read_widget = cls._get_read_widget(attribute.datatype)
                write_widget = cls._get_write_widget(attribute.datatype)
                return SignalRW(name, pv, write_widget, pv + "_RBV", read_widget)
            case AttrR():
                read_widget = cls._get_read_widget(attribute.datatype)
                return SignalR(name, pv, read_widget)
            case AttrW():
                write_widget = cls._get_write_widget(attribute.datatype)
                return SignalW(name, pv, TextWrite())

    @classmethod
    def _get_command_component(cls, attr_path: str, name: str):
        pv = cls._get_pv(attr_path, name)
        name = name.title().replace("_", " ")

        return SignalX(name, pv, value=1)

    def create_gui(self, options: EpicsGUIOptions | None = None) -> None:
        if options is None:
            options = EpicsGUIOptions()

        if options.file_format is EpicsGUIFormat.edl:
            raise FastCSException("FastCS does not support .edl screens.")

        assert options.output_path.suffix == options.file_format.value

        formatter = deserialize_yaml(Formatter, FORMATTER_YAML)

        components: Tree[Component] = []
        for single_mapping in self._mapping.get_controller_mappings():
            attr_path = single_mapping.controller.path

            group_name = type(single_mapping.controller).__name__ + " " + attr_path
            group_children: list[Component] = []

            for attr_name, attribute in single_mapping.attributes.items():
                group_children.append(
                    self._get_attribute_component(
                        attr_path,
                        attr_name,
                        attribute,
                    )
                )

            for name in single_mapping.command_methods:
                group_children.append(self._get_command_component(attr_path, name))

            components.append(Group(group_name, Grid(), group_children))

        device = Device("Simple Device", children=components)

        formatter.format(device, "MY-DEVICE-PREFIX", options.output_path)
