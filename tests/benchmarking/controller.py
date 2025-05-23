from fastcs import FastCS
from fastcs.attributes import AttrR, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Int
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import EpicsIOCOptions
from fastcs.transport.rest.options import RestOptions, RestServerOptions
from fastcs.transport.tango.options import TangoDSROptions, TangoOptions


class MyTestController(Controller):
    read_int: AttrR = AttrR(Int(), initial_value=0)
    write_bool: AttrW = AttrW(Bool())


def run():
    transport_options = [
        RestOptions(rest=RestServerOptions(port=8090)),
        EpicsCAOptions(
            ca_ioc=EpicsIOCOptions(pv_prefix="BENCHMARK-DEVICE"),
        ),
        TangoOptions(dsr=TangoDSROptions(dev_name="MY/BENCHMARK/DEVICE")),
    ]
    instance = FastCS(
        MyTestController(),
        transport_options,
    )
    instance.run()


if __name__ == "__main__":
    run()
