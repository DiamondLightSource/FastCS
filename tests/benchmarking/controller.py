from fastcs import FastCS
from fastcs.attributes import AttrR, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Int
from fastcs.transport.epics.options import EpicsBackend, EpicsIOCOptions, EpicsOptions
from fastcs.transport.rest.options import RestOptions, RestServerOptions
from fastcs.transport.tango.options import TangoDSROptions, TangoOptions


class TestController(Controller):
    read_int: AttrR = AttrR(Int(), initial_value=0)
    write_bool: AttrW = AttrW(Bool())


def run():
    transport_options = [
        RestOptions(rest=RestServerOptions(port=8090)),
        EpicsOptions(
            ioc=EpicsIOCOptions(pv_prefix="BENCHMARK-DEVICE"),
            backend=EpicsBackend.SOFT_IOC,
        ),
        TangoOptions(dsr=TangoDSROptions(dev_name="MY/BENCHMARK/DEVICE")),
    ]
    instance = FastCS(
        TestController(),
        transport_options,
    )
    instance.run()


if __name__ == "__main__":
    run()
