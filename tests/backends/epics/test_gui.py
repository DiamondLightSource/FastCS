from fastcs.backends.epics.gui import EpicsGUI
from fastcs.controller import Controller
from fastcs.mapping import Mapping


def test_get_pv():
    gui = EpicsGUI(Mapping(Controller()), "DEVICE")

    assert gui._get_pv([], "A") == "DEVICE:A"
    assert gui._get_pv(["B"], "C") == "DEVICE:B:C"
    assert gui._get_pv(["D", "E"], "F") == "DEVICE:D:E:F"
