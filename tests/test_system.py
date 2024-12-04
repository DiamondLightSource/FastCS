import contextlib
import multiprocessing
import os

import pytest
import requests
import tango
from p4p.client.thread import Context

SKIP_REST = False
REST_CLIENTS = 3
SKIP_CA = False
CA_CLIENTS = 3
SKIP_TANGO = False
TANGO_CLIENTS = 3

os.environ["FASTCS_PERFORMANCE"] = "true"
os.environ["TANGO_HOST"] = "localhost:10000"
FASTCS_PERFORMANCE = os.getenv("FASTCS_PERFORMANCE") == "true"


def to_do(event, url):
    while not event.is_set():
        requests.get(url)


@contextlib.contextmanager
def start_background_traffic(rest_target):
    """Context manager to handle the lifecycle of a process."""
    stop_event = multiprocessing.Event()
    process = multiprocessing.Process(target=to_do, args=(stop_event, rest_target))
    process.start()

    try:
        yield process
    finally:
        stop_event.set()  # Signal the process to stop
        process.join()  # Wait for the process to finish


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_REST, reason="Skip rest")
@pytest.mark.benchmark(
    group="test-rest",
)
def test_rest_get(benchmark):
    def to_do():
        requests.get("http://localhost:8080/readback-position")

    benchmark(to_do)


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_REST, reason="Skip rest")
@pytest.mark.benchmark(
    group="test-rest",
)
def test_rest_get_loaded(benchmark):
    def to_do():
        requests.get("http://localhost:8080/readback-position")

    with start_background_traffic("http://localhost:8080/readback-position"):
        benchmark(to_do)


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_REST, reason="Skip rest")
@pytest.mark.benchmark(
    group="test-rest",
)
def test_rest_put(benchmark):
    def to_do():
        requests.put("http://localhost:8080/desired-position", json={"value": "false"})

    benchmark(to_do)


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_CA, reason="Skip CA")
@pytest.mark.benchmark(
    group="test-ca",
)
def test_ca_get(benchmark):
    ctx = Context("pva")

    def to_do():
        ctx.get("MY-DEVICE-PREFIX:ReadbackPosition")

    benchmark(to_do)


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_CA, reason="Skip CA")
@pytest.mark.benchmark(
    group="test-ca",
)
def test_ca_put(benchmark):
    ctx = Context("pva")

    def to_do():
        ctx.put("MY-DEVICE-PREFIX:DesiredPosition", 0)

    benchmark(to_do)


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_TANGO, reason="Skip Tango")
@pytest.mark.benchmark(
    group="test-tango",
)
def test_tango_get(benchmark):
    device = tango.DeviceProxy("MY/DEVICE/NAME")

    def to_do():
        device.read_attribute("ReadbackPosition")

    benchmark(to_do)


@pytest.mark.skipif(not FASTCS_PERFORMANCE, reason="Hardware dependant")
@pytest.mark.skipif(SKIP_TANGO, reason="Skip Tango")
@pytest.mark.benchmark(
    group="test-tango",
)
def test_tango_put(benchmark):
    device = tango.DeviceProxy("MY/DEVICE/NAME")

    def to_do():
        device.write_attribute("DesiredPosition", 0)

    benchmark(to_do)
