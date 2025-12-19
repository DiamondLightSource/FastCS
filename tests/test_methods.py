import pytest

from fastcs.controllers import Controller
from fastcs.methods import Command, Scan
from fastcs.methods.command import UnboundCommand
from fastcs.methods.method import Method
from fastcs.methods.scan import UnboundScan


def test_method():
    def sync_do_nothing():
        pass

    with pytest.raises(TypeError):
        Method(sync_do_nothing)  # type: ignore

    async def do_nothing_with_return() -> int:
        return 1

    with pytest.raises(TypeError):
        Method(do_nothing_with_return)  # type: ignore

    async def do_nothing():
        """Do nothing."""
        pass

    method = Method(do_nothing, group="Nothing")

    assert method.docstring == "Do nothing."
    assert method.group == "Nothing"


@pytest.mark.asyncio
async def test_unbound_command():
    class TestController(Controller):
        async def do_nothing(self):
            pass

        async def do_nothing_with_arg(self, arg):
            pass

    with pytest.raises(TypeError):
        UnboundCommand(TestController.do_nothing_with_arg)  # type: ignore

    with pytest.raises(TypeError):
        Command(TestController().do_nothing_with_arg)  # type: ignore

    unbound_command = UnboundCommand(TestController.do_nothing, group="Test")
    command = unbound_command.bind(TestController())
    # Test that group is passed when binding commands
    assert command.group == "Test"

    await command()


@pytest.mark.asyncio
async def test_unbound_scan():
    class TestController(Controller):
        async def update_nothing(self):
            pass

        async def update_nothing_with_arg(self, arg):
            pass

    with pytest.raises(TypeError):
        UnboundScan(TestController.update_nothing_with_arg, 1.0)  # type: ignore

    with pytest.raises(TypeError):
        Scan(TestController().update_nothing_with_arg, 1.0)  # type: ignore

    unbound_scan = UnboundScan(TestController.update_nothing, 1.0)
    assert unbound_scan.period == 1.0
    scan = unbound_scan.bind(TestController())

    assert scan.period == 1.0

    await scan()
