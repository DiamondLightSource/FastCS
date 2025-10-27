import asyncio
from dataclasses import dataclass

import pytest

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import ONCE, AttrR, AttrRW
from fastcs.control_system import FastCS, build_controller_api
from fastcs.controller import Controller
from fastcs.cs_methods import Command
from fastcs.datatypes import Int
from fastcs.exceptions import FastCSError
from fastcs.wrappers import command, scan


@pytest.mark.asyncio
async def test_scan_tasks(controller):
    loop = asyncio.get_event_loop()
    transport_options = []
    fastcs = FastCS(controller, transport_options, loop)

    asyncio.create_task(fastcs.serve(interactive=False))
    await asyncio.sleep(0.1)

    for _ in range(3):
        count = controller.count
        await asyncio.sleep(controller.counter.period + 0.01)
        assert controller.count > count


def test_controller_api():
    class MyTestController(Controller):
        attr1: AttrRW[int] = AttrRW(Int())

        def __init__(self):
            super().__init__(description="Controller for testing")

            self.attributes["attr2"] = AttrRW(Int())

        @command()
        async def do_nothing(self):
            pass

        @scan(1.0)
        async def scan_nothing(self):
            pass

    controller = MyTestController()
    api = build_controller_api(controller)

    assert api.description == controller.description
    assert list(api.attributes) == ["attr1", "attr2"]
    assert list(api.command_methods) == ["do_nothing"]
    assert list(api.scan_methods) == ["scan_nothing"]


@pytest.mark.asyncio
async def test_controller_api_methods():
    class MyTestController(Controller):
        def __init__(self):
            super().__init__()

        async def initialise(self):
            async def do_nothing_dynamic() -> None:
                pass

            self.do_nothing_dynamic = Command(do_nothing_dynamic)

        @command()
        async def do_nothing_static(self):
            pass

    controller = MyTestController()
    loop = asyncio.get_event_loop()
    transport_options = []
    fastcs = FastCS(controller, transport_options, loop)

    asyncio.create_task(fastcs.serve(interactive=False))
    await asyncio.sleep(0.1)

    await controller.do_nothing_static()
    await controller.do_nothing_dynamic()

    await fastcs.controller_api.command_methods["do_nothing_static"]()
    await fastcs.controller_api.command_methods["do_nothing_dynamic"]()


@pytest.mark.asyncio
async def test_update_periods():
    @dataclass
    class AttributeIORefTimesCalled(AttributeIORef):
        update_period: float | None = None
        _times_called = 0

    class AttributeIOTimesCalled(AttributeIO[int, AttributeIORefTimesCalled]):
        async def update(self, attr: AttrR[int, AttributeIORefTimesCalled]):
            attr.io_ref._times_called += 1
            await attr.update(attr.io_ref._times_called)

    class MyController(Controller):
        update_once = AttrR(Int(), io_ref=AttributeIORefTimesCalled(update_period=ONCE))
        update_quickly = AttrR(
            Int(), io_ref=AttributeIORefTimesCalled(update_period=0.1)
        )
        update_never = AttrR(
            Int(), io_ref=AttributeIORefTimesCalled(update_period=None)
        )

    controller = MyController(ios=[AttributeIOTimesCalled()])
    loop = asyncio.get_event_loop()
    transport_options = []

    fastcs = FastCS(controller, transport_options, loop)

    assert controller.update_quickly.get() == 0
    assert controller.update_once.get() == 0
    assert controller.update_never.get() == 0

    asyncio.create_task(fastcs.serve(interactive=False))
    await asyncio.sleep(0.5)

    assert controller.update_quickly.get() > 1
    assert controller.update_once.get() == 1
    assert controller.update_never.get() == 0

    assert len(fastcs._scan_tasks) == 1
    assert len(fastcs._initial_coros) == 1


@pytest.mark.asyncio
async def test_scan_raises_exception_via_callback():
    class MyTestController(Controller):
        def __init__(self):
            super().__init__()

        @scan(0.1)
        async def raise_exception(self):
            raise ValueError("Scan Exception")

    controller = MyTestController()
    loop = asyncio.get_event_loop()
    transport_options = []
    fastcs = FastCS(controller, transport_options, loop)

    exception_info = {}
    # This will intercept the exception raised in _scan_done
    loop.set_exception_handler(
        lambda _loop, context: exception_info.update(
            {"exception": context.get("exception")}
        )
    )

    task = asyncio.create_task(fastcs.serve(interactive=False))
    # This allows scan time to run
    await asyncio.sleep(0.2)
    # _scan_done should raise an exception
    assert isinstance(exception_info["exception"], FastCSError)
    for task in fastcs._scan_tasks:
        internal_exception = task.exception()
        assert internal_exception
        # The task exception comes from scan method raise_exception
        assert isinstance(internal_exception, ValueError)
        assert "Scan Exception" == str(internal_exception)


@pytest.mark.asyncio
async def test_controller_connect_disconnect():
    class MyTestController(Controller):
        def __init__(self):
            super().__init__()

            self.connected = False

        async def connect(self):
            self.connected = True

        async def disconnect(self):
            self.connected = False

    controller = MyTestController()

    loop = asyncio.get_event_loop()
    fastcs = FastCS(controller, [], loop)

    task = asyncio.create_task(fastcs.serve(interactive=False))

    # connect is called at the start of serve
    await asyncio.sleep(0.1)
    assert controller.connected

    task.cancel()

    # disconnect is called at the end of serve
    await asyncio.sleep(0.1)
    assert not controller.connected
