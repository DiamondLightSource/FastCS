import os

import pytest

from fastcs.attributes import AttrR, AttrRW, AttrW, Handler, Sender, Updater
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.mapping import Mapping
from fastcs.wrappers import command, scan

# Prevent pytest from catching exceptions when debugging in vscode so that break on
# exception works correctly (see: https://github.com/pytest-dev/pytest/issues/7409)
if os.getenv("PYTEST_RAISE", "0") == "1":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
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
