from pvi.device import (
    ButtonPanel,
    SignalR,
    SignalRW,
    SignalW,
    SignalX,
    TextRead,
    TextWrite,
    ToggleButton,
)

from fastcs.backends.epics.gui import EpicsGUI
from fastcs.controller import Controller
from fastcs.mapping import Mapping


def test_get_pv():
    gui = EpicsGUI(Mapping(Controller()), "DEVICE")

    assert gui._get_pv([], "A") == "DEVICE:A"
    assert gui._get_pv(["B"], "C") == "DEVICE:B:C"
    assert gui._get_pv(["D", "E"], "F") == "DEVICE:D:E:F"


def test_get_components(mapping):
    gui = EpicsGUI(mapping, "DEVICE")

    components = gui.extract_mapping_components(mapping.get_controller_mappings()[0])
    assert components == [
        SignalR(
            name="ReadInt",
            read_pv="DEVICE:ReadInt",
            read_widget=TextRead(),
        ),
        SignalR(
            name="ReadString",
            read_pv="DEVICE:ReadString",
            read_widget=TextRead(format="string"),
        ),
        SignalRW(
            name="ReadWriteFloat",
            write_pv="DEVICE:ReadWriteFloat",
            write_widget=TextWrite(),
            read_pv="DEVICE:ReadWriteFloat_RBV",
            read_widget=TextRead(),
        ),
        SignalW(
            name="WriteBool",
            write_pv="DEVICE:WriteBool",
            write_widget=ToggleButton(),
        ),
        SignalX(
            name="Go",
            write_pv="DEVICE:Go",
            write_widget=ButtonPanel(actions={"Go": "1"}),
            value="1",
        ),
    ]
