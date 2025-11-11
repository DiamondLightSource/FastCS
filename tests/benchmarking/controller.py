import asyncio

from fastcs import FastCS
from fastcs.attributes import AttrR, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Int
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.transport.rest.options import RestServerOptions
from fastcs.transport.rest.transport import RestTransport
from fastcs.transport.tango.options import TangoDSROptions
from fastcs.transport.tango.transport import TangoTransport


class MyTestController(Controller):
    read_int: AttrR = AttrR(Int(), initial_value=0)
    write_bool: AttrW = AttrW(Bool())


def run():
    transport_options = [
        RestTransport(rest=RestServerOptions(port=8090)),
        EpicsCATransport(
            epicsca=EpicsIOCOptions(pv_prefix="BENCHMARK-DEVICE"),
        ),
        TangoTransport(tango=TangoDSROptions(dev_name="MY/BENCHMARK/DEVICE")),
    ]
    instance = FastCS(MyTestController(), transport_options, asyncio.get_event_loop())
    instance.run()


if __name__ == "__main__":
    run()
