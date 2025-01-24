import contextlib
import multiprocessing
import os

import pytest
import requests
import tango
from p4p.client.thread import Context

FASTCS_BENCHMARKING = os.getenv("FASTCS_BENCHMARKING") == "true"
GET_ENDPOINT = "http://localhost:8090/read-int"
PUT_ENDPOINT = "http://localhost:8090/write-bool"
GET_PV = "BENCHMARK-DEVICE:ReadInt"
PUT_PV = "BENCHMARK-DEVICE:WriteBool"
TANGO_DEVICE = "MY/BENCHMARK/DEVICE"
READ_ATTR = "ReadInt"
WRITE_ATTR = "WriteBool"
REST_CLIENTS = 9
os.environ["TANGO_HOST"] = "localhost:10000"


def rest_get():
    requests.get(GET_ENDPOINT)


def rest_put():
    requests.put(PUT_ENDPOINT, json={"value": "false"})


ctx = Context("pva")


def epics_get():
    ctx.get(GET_PV)


def epics_put():
    ctx.put(PUT_PV, 0)


def bg_get(event, url):
    """Workload for a rest subprocess."""
    while not event.is_set():
        requests.get(url)


def bg_pass(event, url):
    """Workload for a rest subprocess."""
    while not event.is_set():
        pass


@contextlib.contextmanager
def background_traffic(rest_target):
    """Context manager to manage background clients"""
    stop_event = multiprocessing.Event()
    processes = [
        multiprocessing.Process(
            target=bg_get if rest_target else bg_pass,
            args=(stop_event, rest_target),
        )
        for _ in range(REST_CLIENTS)
    ]
    for process in processes:
        process.start()

    try:
        yield processes
    finally:
        # Signal the processes to stop
        stop_event.set()
        # Wait for the processes to finish
        for process in processes:
            process.join()


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-rest")
def test_rest_get(benchmark, test_controller):
    benchmark(rest_get)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-rest")
def test_rest_get_loaded_request(benchmark, test_controller):
    with background_traffic(GET_ENDPOINT):
        benchmark(rest_get)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-rest")
def test_rest_get_loaded_baseline(benchmark, test_controller):
    with background_traffic(None):
        benchmark(rest_get)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-rest")
def test_rest_put(benchmark, test_controller):
    benchmark(rest_put)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-epics")
def test_epics_get(benchmark, test_controller):
    benchmark(epics_get)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-epics")
def test_epics_get_loaded_request(benchmark, test_controller):
    with background_traffic(GET_ENDPOINT):
        benchmark(epics_get)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-epics")
def test_epics_get_loaded_baseline(benchmark, test_controller):
    with background_traffic(None):
        benchmark(epics_get)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-epics")
def test_epics_put(benchmark, test_controller):
    benchmark(epics_put)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-tango")
def test_tango_get(benchmark, test_controller):
    device = tango.DeviceProxy(TANGO_DEVICE)

    def to_do():
        device.read_attribute(READ_ATTR)

    benchmark(to_do)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-tango")
def test_tango_get_loaded_request(benchmark, test_controller):
    device = tango.DeviceProxy(TANGO_DEVICE)

    def to_do():
        device.read_attribute(READ_ATTR)

    with background_traffic(GET_ENDPOINT):
        benchmark(to_do)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-tango")
def test_tango_get_loaded_baseline(benchmark, test_controller):
    device = tango.DeviceProxy(TANGO_DEVICE)

    def to_do():
        device.read_attribute(READ_ATTR)

    with background_traffic(None):
        benchmark(to_do)


@pytest.mark.skipif(not FASTCS_BENCHMARKING, reason="export FASTCS_BENCHMARKING=true")
@pytest.mark.benchmark(group="test-tango")
def test_tango_put(benchmark, test_controller):
    device = tango.DeviceProxy(TANGO_DEVICE)

    def to_do():
        device.write_attribute(WRITE_ATTR, 0)

    benchmark(to_do)
