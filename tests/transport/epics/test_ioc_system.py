from p4p import Value
from p4p.client.thread import Context


def test_ioc(ioc: None):
    ctxt = Context("pva")

    _parent_pvi = ctxt.get("DEVICE:PVI")
    assert isinstance(_parent_pvi, Value)
    parent_pvi = _parent_pvi.todict()
    assert all(f in parent_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert parent_pvi["display"] == {"description": "The records in this controller"}
    assert parent_pvi["value"] == {
        "a": {"r": "DEVICE:A"},
        "b": {"r": "DEVICE:B_RBV", "w": "DEVICE:B"},
        "child": {"d": "DEVICE:Child:PVI"},
    }

    child_pvi_pv = parent_pvi["value"]["child"]["d"]
    _child_pvi = ctxt.get(child_pvi_pv)
    assert isinstance(_child_pvi, Value)
    child_pvi = _child_pvi.todict()
    assert all(f in child_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert child_pvi["display"] == {"description": "The records in this controller"}
    assert child_pvi["value"] == {
        "c": {"w": "DEVICE:Child:C"},
        "d": {"x": "DEVICE:Child:D"},
    }
