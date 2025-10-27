import pytest

from fastcs.controller import Controller
from fastcs.cs_methods import Command, Method, Scan, UnboundCommand, UnboundScan
from fastcs.exceptions import FastCSError


def test_method():
    def sync_do_nothing():
        pass

    with pytest.raises(FastCSError):
        Method(sync_do_nothing)  # type: ignore

    async def do_nothing_with_return() -> int:
        return 1

    with pytest.raises(FastCSError):
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

    unbound_command = UnboundCommand(TestController.do_nothing, group="Test")

    with pytest.raises(NotImplementedError):
        await unbound_command()

    with pytest.raises(FastCSError):
        UnboundCommand(TestController.do_nothing_with_arg)  # type: ignore

    with pytest.raises(FastCSError):
        Command(TestController().do_nothing_with_arg)  # type: ignore

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

    unbound_scan = UnboundScan(TestController.update_nothing, 1.0)

    assert unbound_scan.period == 1.0

    with pytest.raises(NotImplementedError):
        await unbound_scan()

    with pytest.raises(FastCSError):
        UnboundScan(TestController.update_nothing_with_arg, 1.0)  # type: ignore

    with pytest.raises(FastCSError):
        Scan(TestController().update_nothing_with_arg, 1.0)  # type: ignore

    scan = unbound_scan.bind(TestController())

    assert scan.period == 1.0

    await scan()
