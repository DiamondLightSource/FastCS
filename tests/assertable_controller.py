import copy
from contextlib import contextmanager
from typing import Literal

from pytest_mock import MockerFixture, MockType

from fastcs.attributes import AttrHandlerR, AttrHandlerRW, AttrHandlerW, AttrR
from fastcs.backend import build_controller_api
from fastcs.controller import Controller, SubController
from fastcs.controller_api import ControllerAPI
from fastcs.datatypes import Int
from fastcs.wrappers import command, scan


class TestUpdater(AttrHandlerR):
    update_period = 1

    async def initialise(self, controller) -> None:
        self.controller = controller

    async def update(self, attr):
        print(f"{self.controller} update {attr}")


class TestSetter(AttrHandlerW):
    async def initialise(self, controller) -> None:
        self.controller = controller

    async def put(self, attr, value):
        print(f"{self.controller}: {attr} = {value}")


class TestHandler(AttrHandlerRW, TestUpdater, TestSetter):
    pass


class TestSubController(SubController):
    read_int: AttrR = AttrR(Int(), handler=TestUpdater())


class MyTestController(Controller):
    def __init__(self) -> None:
        super().__init__()

        self._sub_controllers: list[TestSubController] = []
        for index in range(1, 3):
            controller = TestSubController()
            self._sub_controllers.append(controller)
            self.register_sub_controller(f"SubController{index:02d}", controller)

    initialised = False
    connected = False
    count = 0

    async def initialise(self) -> None:
        await super().initialise()
        self.initialised = True

    async def connect(self) -> None:
        self.connected = True

    @command()
    async def go(self):
        pass

    @scan(0.01)
    async def counter(self):
        self.count += 1


class AssertableControllerAPI(ControllerAPI):
    def __init__(self, controller: Controller, mocker: MockerFixture) -> None:
        super().__init__()

        self.mocker = mocker
        self.command_method_spys: dict[str, MockType] = {}

        # Build a ControllerAPI from the given Controller
        controller_api = build_controller_api(controller)
        # Copy its fields
        self.attributes = controller_api.attributes
        self.command_methods = controller_api.command_methods
        self.put_methods = controller_api.put_methods
        self.scan_methods = controller_api.scan_methods
        self.sub_apis = controller_api.sub_apis

        # Create spys for command methods before they are passed to the transport
        for command_name in self.command_methods.keys():
            self.command_method_spys[command_name] = mocker.spy(
                self.command_methods[command_name], "_fn"
            )

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
        controller_api = self
        item_name = queue.pop(-1)
        for item in queue:
            controller_api = controller_api.sub_apis[item]

        # Get spy
        if method:
            attr = controller_api.attributes[item_name]
            spy = self.mocker.spy(attr, method)
        else:
            # Lookup pre-defined spy for method
            spy = self.command_method_spys[item_name]

        initial = spy.call_count
        try:
            yield  # Enter context
        except Exception as e:
            raise e
        else:  # Exit context
            final = spy.call_count
            assert final == initial + 1, (
                f"Expected {'.'.join(path + [method] if method else path)} "
                f"to be called once, but it was called {final - initial} times."
            )
