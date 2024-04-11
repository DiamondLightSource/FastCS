from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pvi._format.dls import DLSFormatter
from pvi.device import (
    LED,
    ButtonPanel,
    Component,
    Device,
    Grid,
    Group,
    ReadWidget,
    SignalR,
    SignalRW,
    SignalW,
    SignalX,
    SubScreen,
    TextFormat,
    TextRead,
    TextWrite,
    ToggleButton,
    Tree,
    WriteWidget,
)

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.cs_methods import Command
from fastcs.datatypes import Bool, DataType, Float, Int, String
from fastcs.exceptions import FastCSException
from fastcs.mapping import Mapping, SingleMapping


class EpicsGUIFormat(Enum):
    bob = ".bob"
    edl = ".edl"


@dataclass
class EpicsGUIOptions:
    output_path: Path = Path.cwd() / "output.bob"
    file_format: EpicsGUIFormat = EpicsGUIFormat.bob


class EpicsGUI:
    def __init__(self, mapping: Mapping, pv_prefix: str) -> None:
        self._mapping = mapping
        self._pv_prefix = pv_prefix

    def _get_pv(self, attr_path: str, name: str):
        if attr_path:
            attr_path = ":" + attr_path
        attr_path += ":"

        return f"{self._pv_prefix}{attr_path.upper()}{name.title().replace('_', '')}"

    @staticmethod
    def _get_read_widget(datatype: DataType) -> ReadWidget:
        match datatype:
            case Bool():
                return LED()
            case Int() | Float():
                return TextRead()
            case String():
                return TextRead(format=TextFormat.string)
            case _:
                raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")

    @staticmethod
    def _get_write_widget(datatype: DataType) -> WriteWidget:
        match datatype:
            case Bool():
                return ToggleButton()
            case Int() | Float():
                return TextWrite()
            case String():
                return TextWrite(format=TextFormat.string)
            case _:
                raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")

    def _get_attribute_component(self, attr_path: str, name: str, attribute: Attribute):
        pv = self._get_pv(attr_path, name)
        name = name.title().replace("_", "")

        match attribute:
            case AttrRW():
                read_widget = self._get_read_widget(attribute.datatype)
                write_widget = self._get_write_widget(attribute.datatype)
                return SignalRW(
                    name=name,
                    write_pv=pv,
                    write_widget=write_widget,
                    read_pv=pv + "_RBV",
                    read_widget=read_widget,
                )
            case AttrR():
                read_widget = self._get_read_widget(attribute.datatype)
                return SignalR(name=name, read_pv=pv, read_widget=read_widget)
            case AttrW():
                write_widget = self._get_write_widget(attribute.datatype)
                return SignalW(name=name, write_pv=pv, write_widget=TextWrite())

    def _get_command_component(self, attr_path: str, name: str):
        pv = self._get_pv(attr_path, name)
        name = name.title().replace("_", "")

        return SignalX(
            name=name,
            write_pv=pv,
            value="1",
            write_widget=ButtonPanel(actions={name: "1"}),
        )

    def create_gui(self, options: EpicsGUIOptions | None = None) -> None:
        if options is None:
            options = EpicsGUIOptions()

        if options.file_format is EpicsGUIFormat.edl:
            raise FastCSException("FastCS does not support .edl screens.")

        assert options.output_path.suffix == options.file_format.value

        formatter = DLSFormatter()

        controller_mapping = self._mapping.get_controller_mappings()[0]
        sub_controller_mappings = self._mapping.get_controller_mappings()[1:]

        components = self.extract_mapping_components(controller_mapping)

        for sub_controller_mapping in sub_controller_mappings:
            components.append(
                Group(
                    name=sub_controller_mapping.controller.path,
                    layout=SubScreen(),
                    children=self.extract_mapping_components(sub_controller_mapping),
                )
            )

        device = Device(label="Simple Device", children=components)

        formatter.format(device, options.output_path)

    def extract_mapping_components(self, mapping: SingleMapping) -> list[Component]:
        components: Tree[Component] = []
        attr_path = mapping.controller.path

        groups: dict[str, list[Component]] = {}
        for attr_name, attribute in mapping.attributes.items():
            signal = self._get_attribute_component(
                attr_path,
                attr_name,
                attribute,
            )

            match attribute:
                case Attribute(group=group) if group is not None:
                    if group not in groups:
                        groups[group] = []

                    groups[group].append(signal)
                case _:
                    components.append(signal)

        for name, command in mapping.command_methods.items():
            signal = self._get_command_component(attr_path, name)

            match command:
                case Command(group=group) if group is not None:
                    if group not in groups:
                        groups[group] = []

                    groups[group].append(signal)
                case _:
                    components.append(signal)

        for name, children in groups.items():
            components.append(Group(name=name, layout=Grid(), children=children))

        return components
