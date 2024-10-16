import pytest

from fastcs.backend import Backend
from fastcs.controller import Controller, SubController
from fastcs.cs_methods import BoundCommand
from fastcs.mapping import _walk_mappings, get_single_mapping
from fastcs.wrappers import command


def test_controller_nesting():
    controller = Controller()
    sub_controller = SubController()
    sub_sub_controller = SubController()

    controller.register_sub_controller("a", sub_controller)
    sub_controller.register_sub_controller("b", sub_sub_controller)

    assert sub_controller.path == ["a"]
    assert sub_sub_controller.path == ["a", "b"]
    assert list(_walk_mappings(controller)) == [
        get_single_mapping(controller),
        get_single_mapping(sub_controller),
        get_single_mapping(sub_sub_controller),
    ]

    with pytest.raises(
        ValueError, match=r"Controller .* already has a SubController registered as .*"
    ):
        controller.register_sub_controller("a", SubController())

    with pytest.raises(
        ValueError, match=r"SubController is already registered under .*"
    ):
        controller.register_sub_controller("c", sub_controller)


@pytest.mark.asyncio
async def test_controller_methods():
    class TestController(Controller):
        def __init__(self):
            super().__init__()
            self.do_nothing2 = BoundCommand(self.do_nothing2)

        @command()
        async def do_nothing(self):
            pass

        async def do_nothing2(self):
            pass

    c = TestController()
    await c.do_nothing()
    await c.do_nothing2()
    b = Backend(c)
    await b._mapping.get_controller_mappings()[0].command_methods["do_nothing"]()
    await b._mapping.get_controller_mappings()[0].command_methods["do_nothing2"]()
