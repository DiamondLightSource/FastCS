from pvi.device import (
    LED,
    ButtonPanel,
    ComboBox,
    Group,
    SignalR,
    SignalRW,
    SignalW,
    SignalX,
    SubScreen,
    TextFormat,
    TextRead,
    TextWrite,
    ToggleButton,
)

from fastcs.transport.epics.gui import EpicsGUI


def test_get_pv(controller):
    gui = EpicsGUI(controller, "DEVICE")

    assert gui._get_pv([], "A") == "DEVICE:A"
    assert gui._get_pv(["B"], "C") == "DEVICE:B:C"
    assert gui._get_pv(["D", "E"], "F") == "DEVICE:D:E:F"


def test_get_components(controller):
    gui = EpicsGUI(controller, "DEVICE")

    components = gui.extract_mapping_components(controller.get_controller_mappings()[0])
    assert components == [
        Group(
            name="SubController01",
            layout=SubScreen(labelled=True),
            children=[
                SignalR(
                    name="ReadInt",
                    read_pv="DEVICE:SubController01:ReadInt",
                    read_widget=TextRead(),
                )
            ],
        ),
        Group(
            name="SubController02",
            layout=SubScreen(labelled=True),
            children=[
                SignalR(
                    name="ReadInt",
                    read_pv="DEVICE:SubController01:ReadInt",
                    read_widget=TextRead(),
                )
            ],
        ),
        SignalR(name="BigEnum", read_pv="DEVICE:BigEnum", read_widget=TextRead()),
        SignalR(name="ReadBool", read_pv="DEVICE:ReadBool", read_widget=LED()),
        SignalR(
            name="ReadInt",
            read_pv="DEVICE:ReadInt",
            read_widget=TextRead(),
        ),
        SignalRW(
            name="ReadWriteFloat",
            write_pv="DEVICE:ReadWriteFloat",
            write_widget=TextWrite(),
            read_pv="DEVICE:ReadWriteFloat_RBV",
            read_widget=TextRead(),
        ),
        SignalRW(
            name="ReadWriteInt",
            write_pv="DEVICE:ReadWriteInt",
            write_widget=TextWrite(),
            read_pv="DEVICE:ReadWriteInt_RBV",
            read_widget=TextRead(),
        ),
        SignalRW(
            name="StringEnum",
            read_pv="DEVICE:StringEnum_RBV",
            read_widget=TextRead(format=TextFormat.string),
            write_pv="DEVICE:StringEnum",
            write_widget=ComboBox(choices=["red", "green", "blue"]),
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
