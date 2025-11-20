from pvi.device import (
    CheckBox,
    ReadWidgetUnion,
    TableRead,
    TableWrite,
    WriteWidgetUnion,
)

from fastcs.datatypes import Bool, DataType, Table
from fastcs.transport.epics.gui import EpicsGUI
from fastcs.util import numpy_to_fastcs_datatype


class PvaEpicsGUI(EpicsGUI):
    """For creating gui in the PVA EPICS transport."""

    def _get_pv(self, attr_path: list[str], name: str):
        return f"pva://{super()._get_pv(attr_path, name)}"

    def _get_read_widget(self, fastcs_datatype: DataType) -> ReadWidgetUnion | None:  # noqa: F821
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
