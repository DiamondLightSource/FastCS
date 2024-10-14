import os
import random
import string
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from aioca import purge_channel_caches

from fastcs.attributes import AttrR, AttrRW, AttrW, Handler, Sender, Updater
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.mapping import Mapping
from fastcs.wrappers import command, scan

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


class TestController(Controller):
    read_int: AttrR = AttrR(Int(), handler=TestUpdater())
    read_write_int: AttrRW = AttrRW(Int(), handler=TestHandler())
    read_write_float: AttrRW = AttrRW(Float())
    read_bool: AttrR = AttrR(Bool())
    write_bool: AttrW = AttrW(Bool(), handler=TestSender())
    string_enum: AttrRW = AttrRW(String(), allowed_values=["red", "green", "blue"])
    big_enum: AttrR = AttrR(
        Int(),
        allowed_values=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
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


@pytest.fixture
def controller():
    return TestController()


@pytest.fixture
def mapping(controller):
    return Mapping(controller)


PV_PREFIX = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
HERE = Path(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def ioc():
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
        if time.monotonic() - start_time > 10:
            raise TimeoutError("IOC did not start in time")

    yield

    # close backend caches before the event loop
    purge_channel_caches()
    try:
        print(process.communicate("exit")[0])
    except ValueError:
        # Someone else already called communicate
        pass
