from pvi._format.dls import DLSFormatter  # type: ignore
from pvi.device import (
    LED,
    ButtonPanel,
    CheckBox,
    ComboBox,
    ComponentUnion,
    Device,
    Grid,
    Group,
    ReadWidgetUnion,
    SignalR,
    SignalRW,
    SignalW,
    SignalX,
    SubScreen,
    TableRead,
    TableWrite,
    TextFormat,
    TextRead,
    TextWrite,
    ToggleButton,
    Tree,
    WriteWidgetUnion,
)
from pydantic import ValidationError

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller_api import ControllerAPI
from fastcs.cs_methods import Command
from fastcs.datatypes import (
    Bool,
    DataType,
    Enum,
    Float,
    Int,
    String,
    Table,
    Waveform,
)
from fastcs.exceptions import FastCSException
from fastcs.util import numpy_to_fastcs_datatype, snake_to_pascal

from .options import EpicsGUIFormat, EpicsGUIOptions


class EpicsGUI:
    """For creating gui in the EPICS transports."""

    def __init__(self, controller_api: ControllerAPI, pv_prefix: str) -> None:
        self._controller_api = controller_api
        self._pv_prefix = pv_prefix

    def _get_pv(self, attr_path: list[str], name: str):
        attr_prefix = ":".join(
            [self._pv_prefix] + [snake_to_pascal(node) for node in attr_path]
        )
        return f"{attr_prefix}:{snake_to_pascal(name)}"

    def _get_read_widget(self, fastcs_datatype: DataType) -> ReadWidgetUnion | None:
        match fastcs_datatype:
            case Bool():
                return LED()
            case Int() | Float():
                return TextRead()
            case String():
                return TextRead(format=TextFormat.string)
            case Enum():
                return TextRead(format=TextFormat.string)
            case Waveform():
                return None
            case datatype:
                raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")

    def _get_write_widget(self, fastcs_datatype: DataType) -> WriteWidgetUnion | None:
        match fastcs_datatype:
            case Bool():
                return ToggleButton()
            case Int() | Float():
                return TextWrite()
            case String():
                return TextWrite(format=TextFormat.string)
            case Enum():
                return ComboBox(choices=fastcs_datatype.names)
            case Waveform():
                return None
            case datatype:
                raise FastCSException(f"Unsupported type {type(datatype)}: {datatype}")

    def _get_attribute_component(
        self, attr_path: list[str], name: str, attribute: Attribute
    ) -> SignalR | SignalW | SignalRW | None:
        pv = self._get_pv(attr_path, name)
        name = snake_to_pascal(name)
        match attribute:
            case AttrRW():
                read_widget = self._get_read_widget(attribute.datatype)
                write_widget = self._get_write_widget(attribute.datatype)
                if write_widget is None or read_widget is None:
                    return None
                return SignalRW(
                    name=name,
                    write_pv=pv,
                    write_widget=write_widget,
                    read_pv=pv + "_RBV",
                    read_widget=read_widget,
                )
            case AttrR():
                read_widget = self._get_read_widget(attribute.datatype)
                if read_widget is None:
                    return None
                return SignalR(name=name, read_pv=pv, read_widget=read_widget)
            case AttrW():
                write_widget = self._get_write_widget(attribute.datatype)
                if write_widget is None:
                    return None
                return SignalW(name=name, write_pv=pv, write_widget=write_widget)
            case _:
                raise FastCSException(f"Unsupported attribute type: {type(attribute)}")

    def _get_command_component(self, attr_path: list[str], name: str):
        pv = self._get_pv(attr_path, name)
        name = snake_to_pascal(name)

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
        options.output_path.parent.mkdir(parents=True, exist_ok=True)

        components = self.extract_api_components(self._controller_api)
        device = Device(label=options.title, children=components)

        formatter = DLSFormatter()
        formatter.format(device, options.output_path.resolve())

    def extract_api_components(self, controller_api: ControllerAPI) -> Tree:
        components: Tree = []

        for name, api in controller_api.sub_apis.items():
            components.append(
                Group(
                    name=snake_to_pascal(name),
                    layout=SubScreen(),
                    children=self.extract_api_components(api),
                )
            )

        groups: dict[str, list[ComponentUnion]] = {}
        for attr_name, attribute in controller_api.attributes.items():
            try:
                signal = self._get_attribute_component(
                    controller_api.path,
                    attr_name,
                    attribute,
                )
            except ValidationError as e:
                print(f"Invalid name:\n{e}")
                continue

            if signal is None:
                continue

            match attribute:
                case Attribute(group=group) if group is not None:
                    if group not in groups:
                        groups[group] = []

                    # Remove duplication of group name and signal name
                    signal.name = signal.name.removeprefix(group)

                    groups[group].append(signal)
                case _:
                    components.append(signal)

        for name, command in controller_api.command_methods.items():
            signal = self._get_command_component(controller_api.path, name)

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


class PvaEpicsGUI(EpicsGUI):
    """For creating gui in the PVA EPICS transport."""

    def _get_pv(self, attr_path: list[str], name: str):
        return f"pva://{super()._get_pv(attr_path, name)}"

    def _get_read_widget(self, fastcs_datatype: DataType) -> ReadWidgetUnion | None:
        if isinstance(fastcs_datatype, Table):
            fastcs_datatypes = [
                numpy_to_fastcs_datatype(datatype)
                for _, datatype in fastcs_datatype.structured_dtype
            ]

            base_get_read_widget = super()._get_read_widget
            widgets = [base_get_read_widget(datatype) for datatype in fastcs_datatypes]

            return TableRead(widgets=widgets)  # type: ignore
        else:
            return super()._get_read_widget(fastcs_datatype)

    def _get_write_widget(self, fastcs_datatype: DataType) -> WriteWidgetUnion | None:
        if isinstance(fastcs_datatype, Table):
            widgets = []
            for _, datatype in fastcs_datatype.structured_dtype:
                fastcs_datatype = numpy_to_fastcs_datatype(datatype)
                if isinstance(fastcs_datatype, Bool):
                    # Replace with compact version for Table row
                    widget = CheckBox()
                else:
                    widget = super()._get_write_widget(fastcs_datatype)
                widgets.append(widget)
            return TableWrite(widgets=widgets)
        else:
            return super()._get_write_widget(fastcs_datatype)
