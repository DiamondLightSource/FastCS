import os
import random
import signal
import string
import subprocess
import time
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


@pytest.fixture(scope="module")
def ioc():
    TIMEOUT = 10
    process = subprocess.Popen(
        ["python", HERE / "ioc.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    start_time = time.monotonic()
    while "iocRun: All initialization complete" not in (
        process.stdout.readline().strip()  # type: ignore
    ):
        if time.monotonic() - start_time > TIMEOUT:
            raise TimeoutError("IOC did not start in time")

    yield

    # close backend caches before the event loop
    purge_channel_caches()

    # Close open files
    for f in [process.stdin, process.stdout, process.stderr]:
        if f:
            f.close()
    process.send_signal(signal.SIGINT)
    process.wait(TIMEOUT)


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
