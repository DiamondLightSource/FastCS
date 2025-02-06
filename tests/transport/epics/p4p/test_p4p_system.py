from p4p import Value
from p4p.client.thread import Context


def test_ioc(p4p_subprocess: None):
    ctxt = Context("pva")

    _parent_pvi = ctxt.get("P4P_TEST_DEVICE:PVI")
    assert isinstance(_parent_pvi, Value)
    parent_pvi = _parent_pvi.todict()
    assert all(f in parent_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert parent_pvi["display"] == {"description": "some controller"}
    assert parent_pvi["value"] == {
        "a": {"r": "P4P_TEST_DEVICE:A"},
        "b": {"rw": "P4P_TEST_DEVICE:B"},
        "child": [
            {"pvi": "P4P_TEST_DEVICE:Child1:PVI"},
            {"pvi": "P4P_TEST_DEVICE:Child2:PVI"},
        ],
    }

    child_pvi_pv = parent_pvi["value"]["child"][0]["pvi"]
    _child_pvi = ctxt.get(child_pvi_pv)
    assert isinstance(_child_pvi, Value)
    child_pvi = _child_pvi.todict()
    assert all(f in child_pvi for f in ("alarm", "display", "timeStamp", "value"))
    assert child_pvi["display"] == {"description": "some sub controller"}
    assert child_pvi["value"] == {
        "c": {"w": "P4P_TEST_DEVICE:Child1:C"},
        "d": {"x": "P4P_TEST_DEVICE:Child1:D"},
        "e": {"r": "P4P_TEST_DEVICE:Child1:E"},
        "f": {"rw": "P4P_TEST_DEVICE:Child1:F"},
        "g": {"rw": "P4P_TEST_DEVICE:Child1:G"},
        "h": {"rw": "P4P_TEST_DEVICE:Child1:H"},
        "i": {"x": "P4P_TEST_DEVICE:Child1:I"},
    }
