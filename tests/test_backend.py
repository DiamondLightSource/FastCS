import asyncio

from fastcs.attributes import AttrRW
from fastcs.backend import Backend, build_controller_api
from fastcs.controller import Controller
from fastcs.cs_methods import Command
from fastcs.datatypes import Int
from fastcs.wrappers import command, scan


def test_backend(controller):
    loop = asyncio.get_event_loop()
    backend = Backend(controller, loop)

    # Controller should be initialised by Backend and not connected
    assert controller.initialised
    assert not controller.connected

    # Controller Attributes with a Sender should have a _process_callback created
    assert controller.read_write_int.has_process_callback()

    async def test_wrapper():
        loop.create_task(backend.serve())
        await asyncio.sleep(0)  # Yield to task

        # Controller should have been connected by Backend
        assert controller.connected

        # Scan tasks should be running
        for _ in range(3):
            count = controller.count
            await asyncio.sleep(0.01)
            assert controller.count > count
        backend._stop_scan_tasks()

    loop.run_until_complete(test_wrapper())


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


def test_controller_api_methods():
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
    backend = Backend(controller, loop)

    async def test_wrapper():
        await controller.do_nothing_static()
        await controller.do_nothing_dynamic()

        await backend.controller_api.command_methods["do_nothing_static"]()
        await backend.controller_api.command_methods["do_nothing_dynamic"]()

    loop.run_until_complete(test_wrapper())
