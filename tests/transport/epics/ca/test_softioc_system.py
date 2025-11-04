from multiprocessing import Queue

from p4p import Value
from p4p.client.thread import Context


def test_ioc(softioc_subprocess: tuple[str, Queue]):
    pv_prefix, _ = softioc_subprocess
    ctxt = Context("pva")

    _parent_pvi = ctxt.get(f"{pv_prefix}:PVI")
    assert isinstance(_parent_pvi, Value)
    parent_pvi = _parent_pvi.todict()
    assert all(f in parent_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert parent_pvi["display"] == {"description": "The records in this controller"}
    assert parent_pvi["value"] == {
        "a": {"r": f"{pv_prefix}:A"},
        "b": {"r": f"{pv_prefix}:B_RBV", "w": f"{pv_prefix}:B"},
        "child": {"d": f"{pv_prefix}:Child:PVI"},
    }

    child_pvi_pv = parent_pvi["value"]["child"]["d"]
    _child_pvi = ctxt.get(child_pvi_pv)
    assert isinstance(_child_pvi, Value)
    child_pvi = _child_pvi.todict()
    assert all(f in child_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert child_pvi["display"] == {"description": "The records in this controller"}
    assert child_pvi["value"] == {
        "c": {"w": f"{pv_prefix}:Child:C"},
        "d": {"x": f"{pv_prefix}:Child:D"},
    }
