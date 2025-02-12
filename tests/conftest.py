import io
import multiprocessing
import os
import random
import signal
import string
import subprocess
import sys
import time
from collections.abc import Callable
from multiprocessing.context import DefaultContext
from pathlib import Path
from typing import Any

import pytest
from aioca import purge_channel_caches

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.transport.tango.dsr import register_dev
from tests.assertable_controller import (
    TestController,
    TestHandler,
    TestSender,
    TestUpdater,
)

from .example_p4p_ioc import run as _run_p4p_ioc
from .example_softioc import run as _run_softioc

DATA_PATH = Path(__file__).parent / "data"


class BackendTestController(TestController):
    read_int: AttrR = AttrR(Int(), handler=TestUpdater())
    read_write_int: AttrRW = AttrRW(Int(), handler=TestHandler())
    read_write_float: AttrRW = AttrRW(Float())
    read_bool: AttrR = AttrR(Bool())
    write_bool: AttrW = AttrW(Bool(), handler=TestSender())
    read_string: AttrRW = AttrRW(String())


@pytest.fixture
def controller():
    return BackendTestController()


@pytest.fixture
def data() -> Path:
    return DATA_PATH


# Prevent pytest from catching exceptions when debugging in vscode so that break on
# exception works correctly (see: https://github.com/pytest-dev/pytest/issues/7409)
if os.getenv("PYTEST_RAISE", "0") == "1":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call: pytest.CallInfo[Any]):
        if call.excinfo is not None:
            raise call.excinfo.value
        else:
            raise RuntimeError(
                f"{call} has no exception data, an unknown error has occurred"
            )

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo: pytest.ExceptionInfo[Any]):
        raise excinfo.value


PV_PREFIX = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
HERE = Path(os.path.dirname(os.path.abspath(__file__)))


def run_softioc(
    error_queue: multiprocessing.Queue, stdout_queue: multiprocessing.Queue
):
    class QueueWriter(io.TextIOBase):
        def __init__(self, queue):
            self.queue = queue

        def write(self, s):  # type: ignore
            self.queue.put(s)

    try:
        sys.stdout = QueueWriter(stdout_queue)
        _run_softioc()

    except Exception as e:
        error_queue.put(e)


def run_p4p_ioc(
    error_queue: multiprocessing.Queue, stdout_queue: multiprocessing.Queue
):
    class QueueWriter(io.TextIOBase):
        def __init__(self, queue):
            self.queue = queue

        def write(self, s):  # type: ignore
            self.queue.put(s)

    try:
        sys.stdout = QueueWriter(stdout_queue)
        _run_p4p_ioc()

    except Exception as e:
        error_queue.put(e)


def run_ioc_as_subprocess(run_ioc: Callable, ctxt: DefaultContext):
    TIMEOUT = 10
    IOC_STARTUP_TIMEOUT_ERROR = TimeoutError("IOC did not start in time")

    error_queue = ctxt.Queue()
    stdout_queue = ctxt.Queue()
    process = ctxt.Process(
        target=run_ioc,
        args=(error_queue, stdout_queue),
    )
    process.start()

    try:
        start_time = time.monotonic()
        while True:
            try:
                if "Running FastCS IOC" in (
                    stdout_queue.get(timeout=TIMEOUT)  # type: ignore
                ):
                    break
            except Exception as error:
                raise IOC_STARTUP_TIMEOUT_ERROR from error
            if time.monotonic() - start_time > TIMEOUT:
                raise IOC_STARTUP_TIMEOUT_ERROR

        yield

        # Propogate errors
        if not error_queue.empty():
            raise error_queue.get()
    finally:
        # close backend caches before the event loop
        purge_channel_caches()

        error_queue.close()
        stdout_queue.close()
        process.terminate()
        process.join(timeout=TIMEOUT)


@pytest.fixture(scope="module")
def p4p_subprocess():
    multiprocessing.set_start_method("forkserver", force=True)
    yield from run_ioc_as_subprocess(run_p4p_ioc, multiprocessing.get_context())


@pytest.fixture(scope="module")
def softioc_subprocess():
    multiprocessing.set_start_method("spawn", force=True)
    yield from run_ioc_as_subprocess(run_softioc, multiprocessing.get_context())


@pytest.fixture(scope="session")
def tango_system():
    subprocess.run(
        ["podman", "compose", "-f", HERE / "benchmarking" / "compose.yaml", "up", "-d"],
        check=True,
    )
    yield
    subprocess.run(
        ["podman", "compose", "-f", HERE / "benchmarking" / "compose.yaml", "down"],
        check=True,
    )


@pytest.fixture(scope="session")
def register_device():
    ATTEMPTS = 10
    SLEEP = 1

    if not os.getenv("TANGO_HOST"):
        raise RuntimeError("TANGO_HOST not defined")

    for attempt in range(1, ATTEMPTS + 1):
        try:
            register_dev(
                dev_name="MY/BENCHMARK/DEVICE",
                dev_class="TestController",
                dsr_instance="MY_SERVER_INSTANCE",
            )
            break
        except Exception:
            time.sleep(SLEEP)
        if attempt == ATTEMPTS:
            raise TimeoutError("Tango device could not be registered")


@pytest.fixture(scope="session")
def test_controller(tango_system, register_device):
    TIMEOUT = 10
    process = subprocess.Popen(
        ["python", HERE / "benchmarking" / "controller.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    start_time = time.monotonic()
    while "Uvicorn running" not in (
        process.stdout.readline().strip()  # type: ignore
    ):
        if time.monotonic() - start_time > TIMEOUT:
            raise TimeoutError("Controller did not start in time")

    # close backend caches before the event loop
    purge_channel_caches()

    # Stop buffer from getting full and blocking the subprocess
    for f in [process.stdin, process.stdout, process.stderr]:
        if f:
            f.close()

    yield process

    process.send_signal(signal.SIGINT)
    process.wait(TIMEOUT)
