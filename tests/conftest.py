import os

import pytest

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Float, Int, String
from fastcs.mapping import Mapping
from fastcs.wrappers import command

# Prevent pytest from catching exceptions when debugging in vscode so that break on
# exception works correctly (see: https://github.com/pytest-dev/pytest/issues/7409)
if os.getenv("PYTEST_RAISE", "0") == "1":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value


class TestController(Controller):
    read_int: AttrR = AttrR(Int())
    read_write_float: AttrRW = AttrRW(Float())
    write_bool: AttrW = AttrW(Bool())
    string_enum: AttrRW = AttrRW(String(), allowed_values=["red", "green", "blue"])

    @command()
    async def go(self):
        pass


@pytest.fixture
def controller():
    return TestController()


@pytest.fixture
def mapping(controller):
    return Mapping(controller)
