from numpy import uint32
from pvi.device import (
    LED,
    SignalR,
    SignalW,
    TableRead,
    TableWrite,
    TextRead,
    TextWrite,
)

from fastcs.attributes import AttrR, AttrW
from fastcs.datatypes import Table
from fastcs.transport.epics.gui import PvaEpicsGUI


def test_get_pv_in_pva(controller_api):
    gui = PvaEpicsGUI(controller_api, "DEVICE")

    assert gui._get_pv([], "A") == "pva://DEVICE:A"
    assert gui._get_pv(["B"], "C") == "pva://DEVICE:B:C"
    assert gui._get_pv(["D", "E"], "F") == "pva://DEVICE:D:E:F"


def test_get_attribute_component_table_write(controller_api):
    gui = PvaEpicsGUI(controller_api, "DEVICE")

    assert gui._get_attribute_component(
        [], "Table", AttrW(Table(structured_dtype=[("FIELD", uint32)]))
    ) == SignalW(
        name="Table", write_pv="Table", write_widget=TableWrite(widgets=[TextWrite()])
    )


def test_get_attribute_component_table_read(controller_api):
    gui = PvaEpicsGUI(controller_api, "DEVICE")

    assert gui._get_attribute_component(
        [], "Table", AttrR(Table(structured_dtype=[("FIELD", uint32)]))
    ) == SignalR(
        name="Table",
        read_pv="Table",
        read_widget=TableRead(
            widgets=[TextRead()] * 4 + [LED()] * 6 + [TextRead()] + [LED()] * 6
        ),
    )
