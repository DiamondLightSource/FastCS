import os
import random
import string
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from aioca import purge_channel_caches

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Float, Int, String
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
    big_enum: AttrR = AttrR(
        Int(
            allowed_values=list(range(17)),
        ),
    )


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
