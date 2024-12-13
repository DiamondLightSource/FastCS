import copy
from contextlib import contextmanager
from typing import Literal

from pytest_mock import MockerFixture

from fastcs.attributes import AttrR, Handler, Sender, Updater
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Int
from fastcs.wrappers import command, scan


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
        self.mocker = mocker
        super().__init__()

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
        except Exception as e:
            raise e
        else:  # Exit context
            final = spy.call_count
            assert final == initial + 1, (
                f"Expected {'.'.join(path + [method] if method else path)} "
                f"to be called once, but it was called {final - initial} times."
            )
