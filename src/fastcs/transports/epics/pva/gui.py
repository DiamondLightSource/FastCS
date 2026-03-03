from pvi.device import (
    CheckBox,
    ImageColorMap,
    ImageRead,
    ReadWidgetUnion,
    TableRead,
    TableWrite,
    WriteWidgetUnion,
)

from fastcs.attributes import Attribute, AttrR, AttrW
from fastcs.datatypes import Bool, Table, Waveform, numpy_to_fastcs_datatype
from fastcs.transports.epics.gui import EpicsGUI


class PvaEpicsGUI(EpicsGUI):
    """For creating gui in the PVA EPICS transport."""

    command_value = "true"

    def _get_pv(self, attr_path: list[str], name: str):
        return f"pva://{super()._get_pv(attr_path, name)}"

    def _get_read_widget(self, attribute: Attribute) -> ReadWidgetUnion | None:
        match attribute.datatype:
            case Table():
                fastcs_datatypes = [
                    numpy_to_fastcs_datatype(datatype)
                    for _, datatype in attribute.datatype.structured_dtype
                ]

                base_get_read_widget = super()._get_read_widget
                widgets = [
                    base_get_read_widget(AttrR(datatype))
                    for datatype in fastcs_datatypes
                ]

                return TableRead(widgets=widgets)  # type: ignore
            case Waveform(shape=(height, width)):
                return ImageRead(
                    height=height, width=width, color_map=ImageColorMap.GRAY
                )
            case _:
                return super()._get_read_widget(attribute)

    def _get_write_widget(self, attribute: Attribute) -> WriteWidgetUnion | None:
        match attribute.datatype:
            case Table():
                widgets = []
                for _, datatype in attribute.datatype.structured_dtype:
                    fastcs_datatype = numpy_to_fastcs_datatype(datatype)
                    if isinstance(fastcs_datatype, Bool):
                        # Replace with compact version for Table row
                        widget = CheckBox()
                    else:
                        widget = super()._get_write_widget(AttrW(fastcs_datatype))
                    widgets.append(widget)
                return TableWrite(widgets=widgets)
            case _:
                return super()._get_write_widget(attribute)
