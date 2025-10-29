import numpy as np
import pytest
from pvi.device import (
    LED,
    ButtonPanel,
    CheckBox,
    ImageRead,
    SignalR,
    SignalW,
    SignalX,
    TableRead,
    TableWrite,
    TextFormat,
    TextRead,
    TextWrite,
)

from fastcs.attributes import AttrR, AttrW
from fastcs.datatypes import Table, Waveform
from fastcs.transports import ControllerAPI
from fastcs.transports.epics.gui import EpicsGUI
from fastcs.transports.epics.pva.gui import PvaEpicsGUI


@pytest.mark.parametrize(
    "datatype, widget",
    [
        (Waveform(array_dtype=np.int32), ImageRead()),
    ],
)
def test_pva_get_attribute_component_r(datatype, widget):
    gui = EpicsGUI(ControllerAPI(), "DEVICE")

    assert gui._get_attribute_component([], "Attr", AttrR(datatype)) == SignalR(
        name="Attr", read_pv="Attr", read_widget=widget
    )


def test_get_pv_in_pva():
    gui = PvaEpicsGUI(ControllerAPI(), "DEVICE")

    assert gui._get_pv([], "A") == "pva://DEVICE:A"
    assert gui._get_pv(["B"], "C") == "pva://DEVICE:B:C"
    assert gui._get_pv(["D", "E"], "F") == "pva://DEVICE:D:E:F"


def test_get_attribute_component_table_write():
    gui = PvaEpicsGUI(ControllerAPI(), "DEVICE")

    attribute_component = gui._get_attribute_component(
        [],
        "Table",
        AttrW(
            Table(
                structured_dtype=[
                    ("FIELD1", np.uint32),
                    ("FIELD2", np.bool),
                    ("FIELD3", np.dtype("S1000")),
                ]
            )
        ),
    )

    assert isinstance(attribute_component, SignalW)
    assert isinstance(attribute_component.write_widget, TableWrite)
    assert attribute_component.write_widget.widgets == [
        TextWrite(),
        CheckBox(),
        TextWrite(format=TextFormat.string),
    ]


def test_get_attribute_component_table_read():
    gui = PvaEpicsGUI(ControllerAPI(), "DEVICE")

    attribute_component = gui._get_attribute_component(
        [],
        "Table",
        AttrR(
            Table(
                structured_dtype=[
                    ("FIELD1", np.uint32),
                    ("FIELD2", np.bool),
                    ("FIELD3", np.dtype("S1000")),
                ]
            )
        ),
    )

    assert isinstance(attribute_component, SignalR)
    assert isinstance(attribute_component.read_widget, TableRead)
    assert attribute_component.read_widget.widgets == [
        TextRead(),
        LED(),
        TextRead(format=TextFormat.string),
    ]


def test_get_command_component():
    gui = PvaEpicsGUI(ControllerAPI(), "DEVICE")

    component = gui._get_command_component([], "Command")

    assert isinstance(component, SignalX)
    assert component.write_widget == ButtonPanel(actions={"Command": "true"})
