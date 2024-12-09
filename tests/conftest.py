import copy
import enum
import os
import random
import signal
import string
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

import pytest
from aioca import purge_channel_caches
from pytest_mock import MockerFixture

from fastcs.attributes import AttrR, AttrRW, AttrW, Handler, Sender, Updater
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.transport.tango.dsr import register_dev
from fastcs.wrappers import command, scan

DATA_PATH = Path(__file__).parent / "data"


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


class TestUpdater(Updater):
    update_period = 1

    async def update(self, controller, attr):
        print(f"{controller} update {attr}")


class TestSender(Sender):
    async def put(self, controller, attr, value):
        print(f"{controller}: {attr} = {value}")


class TestHandler(Handler, TestUpdater, TestSender):
    pass


class TestSubController(SubController):
    read_int: AttrR = AttrR(Int(), handler=TestUpdater())


class TestController(Controller):
    def __init__(self) -> None:
        super().__init__()

        self._sub_controllers: list[TestSubController] = []
        for index in range(1, 3):
            controller = TestSubController()
            self._sub_controllers.append(controller)
            self.register_sub_controller(f"SubController{index:02d}", controller)

    read_int: AttrR = AttrR(Int(), handler=TestUpdater())
    read_write_int: AttrRW = AttrRW(Int(), handler=TestHandler())
    read_write_float: AttrRW = AttrRW(Float())
    read_bool: AttrR = AttrR(Bool())
    write_bool: AttrW = AttrW(Bool(), handler=TestSender())
    read_string: AttrRW = AttrRW(String())
    enum: AttrRW = AttrRW(Enum(enum.IntEnum("Enum", {"RED": 0, "GREEN": 1, "BLUE": 2})))
    big_enum: AttrR = AttrR(
        Int(
            allowed_values=list(range(17)),
        ),
    )

    initialised = False
    connected = False
    count = 0

    async def initialise(self) -> None:
        self.initialised = True

    async def connect(self) -> None:
        self.connected = True

    @command()
    async def go(self):
        pass

    @scan(0.01)
    async def counter(self):
        self.count += 1


class AssertableController(TestController):
    def __init__(self, mocker: MockerFixture) -> None:
        super().__init__()
        self.mocker = mocker

    @contextmanager
    def assert_read_here(self, path: list[str]):
        yield from self._assert_method(path, "get")

    @contextmanager
    def assert_write_here(self, path: list[str]):
        yield from self._assert_method(path, "process")

    @contextmanager
    def assert_execute_here(self, path: list[str]):
        yield from self._assert_method(path, "")

    def _assert_method(self, path: list[str], method: Literal["get", "process", ""]):
        """
        This context manager can be used to confirm that a fastcs
        controller's respective attribute or command methods are called
        a single time within a context block
        """
        queue = copy.deepcopy(path)

        # Navigate to subcontroller
        controller = self
        item_name = queue.pop(-1)
        for item in queue:
            controllers = controller.get_sub_controllers()
            controller = controllers[item]

        # create probe
        if method:
            attr = getattr(controller, item_name)
            spy = self.mocker.spy(attr, method)
        else:
            spy = self.mocker.spy(controller, item_name)
        initial = spy.call_count
        try:
            yield  # Enter context
        finally:  # Exit context
            final = spy.call_count
            assert final == initial + 1, (
                f"Expected {'.'.join(path + [method] if method else path)} "
                f"to be called once, but it was called {final - initial} times."
            )


@pytest.fixture
def controller():
    return TestController()


@pytest.fixture(scope="class")
def assertable_controller(class_mocker: MockerFixture):
    return AssertableController(class_mocker)


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
