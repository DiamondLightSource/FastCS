import asyncio
import json
import os
from dataclasses import dataclass

import pytest
from pydantic import create_model
from pytest_mock import MockerFixture
from ruamel.yaml import YAML
from typer.testing import CliRunner

from fastcs import __version__
from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import ONCE, AttrR, AttrRW
from fastcs.controller import Controller
from fastcs.cs_methods import Command
from fastcs.datatypes import Int
from fastcs.exceptions import FastCSError, LaunchError
from fastcs.launch import (
    FastCS,
    _launch,
    build_controller_api,
    get_controller_schema,
    launch,
)
from fastcs.transport.transport import Transport
from fastcs.wrappers import command, scan


@dataclass
class SomeConfig:
    name: str


class SingleArg(Controller):
    def __init__(self):
        super().__init__()


class NotHinted(Controller):
    def __init__(self, arg):
        super().__init__()


class IsHinted(Controller):
    read = AttrR(Int())

    def __init__(self, arg: SomeConfig) -> None:
        super().__init__()


class ManyArgs(Controller):
    def __init__(self, arg: SomeConfig, too_many):
        super().__init__()


runner = CliRunner()


def test_single_arg_schema():
    target_model = create_model(
        "SingleArg",
        transport=(list[Transport.union()], ...),
        __config__={"extra": "forbid"},
    )
    target_dict = target_model.model_json_schema()

    app = _launch(SingleArg)
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    result_dict = json.loads(result.stdout)

    assert result_dict == target_dict


def test_is_hinted_schema(data):
    target_model = create_model(
        "IsHinted",
        controller=(SomeConfig, ...),
        transport=(list[Transport.union()], ...),
        __config__={"extra": "forbid"},
    )
    target_dict = target_model.model_json_schema()

    app = _launch(IsHinted)
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    result_dict = json.loads(result.stdout)

    assert result_dict == target_dict

    # # store a schema to use for debugging
    # with open(data / "schema.json", mode="w") as f:
    #     json.dump(result_dict, f, indent=2)


def test_not_hinted_schema():
    error = (
        "Expected typehinting in 'NotHinted.__init__' but received "
        "(self, arg). Add a typehint for `arg`."
    )

    with pytest.raises(LaunchError) as exc_info:
        launch(NotHinted)
    assert str(exc_info.value) == error


def test_over_defined_schema():
    error = (
        ""
        "Expected no more than 2 arguments for 'ManyArgs.__init__' "
        "but received 3 as `(self, arg: tests.test_launch.SomeConfig, too_many)`"
    )

    with pytest.raises(LaunchError) as exc_info:
        launch(ManyArgs)
    assert str(exc_info.value) == error


def test_version():
    impl_version = "0.0.1"
    expected = f"SingleArg: {impl_version}\nFastCS: {__version__}\n"
    app = _launch(SingleArg, version=impl_version)
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == expected


def test_no_version():
    expected = f"FastCS: {__version__}\n"
    app = _launch(SingleArg)
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == expected


def test_launch(mocker: MockerFixture, data):
    run = mocker.patch("fastcs.launch.FastCS.run")
    gui = mocker.patch("fastcs.launch.FastCS.create_gui")
    docs = mocker.patch("fastcs.launch.FastCS.create_docs")

    app = _launch(IsHinted)
    result = runner.invoke(app, ["run", str(data / "config.yaml")])
    assert result.exit_code == 0

    run.assert_called_once()
    gui.assert_called_once()
    docs.assert_called_once()


def test_get_schema(data):
    target_schema = get_controller_schema(IsHinted)
    if os.environ.get("FASTCS_REGENERATE_OUTPUT", None):
        with open(data / "schema.json", "w") as f:
            json.dump(target_schema, f, indent=2)

    ref_schema = YAML(typ="safe").load(data / "schema.json")
    assert target_schema == ref_schema


def test_error_if_identical_context_in_transports(mocker: MockerFixture, data):
    mocker.patch("fastcs.launch.FastCS.create_gui")
    mocker.patch("fastcs.launch.FastCS.create_docs")
    mocker.patch(
        "fastcs.transport.Transport.context",
        new_callable=mocker.PropertyMock,
        return_value={"controller": "test"},
    )
    app = _launch(IsHinted)
    result = runner.invoke(app, ["run", str(data / "config.yaml")])
    assert isinstance(result.exception, RuntimeError)
    assert "Duplicate context keys found" in result.exception.args[0]


def test_fastcs(controller):
    loop = asyncio.get_event_loop()
    transport_options = []
    fastcs = FastCS(controller, transport_options, loop)

    # Controller should be initialised by FastCS and not connected
    assert controller.initialised
    assert not controller.connected

    # Controller Attributes with a Sender should have a _process_callback created
    assert controller.read_write_int.has_process_callback()

    async def test_wrapper():
        loop.create_task(fastcs.serve_routines())
        await asyncio.sleep(0)  # Yield to task

        # Controller should have been connected by 'Backend' Logic
        assert controller.connected

        # Scan tasks should be running
        for _ in range(3):
            count = controller.count
            await asyncio.sleep(0.01)
            assert controller.count > count
        fastcs._stop_scan_tasks()

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
    transport_options = []
    fastcs = FastCS(controller, transport_options, loop)

    async def test_wrapper():
        await controller.do_nothing_static()
        await controller.do_nothing_dynamic()

        await fastcs.controller_api.command_methods["do_nothing_static"]()
        await fastcs.controller_api.command_methods["do_nothing_dynamic"]()

    loop.run_until_complete(test_wrapper())


def test_update_periods():
    @dataclass
    class AttributeIORefTimesCalled(AttributeIORef):
        update_period: float | None = None
        _times_called = 0

    class AttributeIOTimesCalled(AttributeIO[int, AttributeIORefTimesCalled]):
        async def update(self, attr: AttrR[int, AttributeIORefTimesCalled]):
            attr.io_ref._times_called += 1
            await attr.set(attr.io_ref._times_called)

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

    async def test_wrapper():
        loop.create_task(fastcs.serve_routines())
        await asyncio.sleep(1)

    loop.run_until_complete(test_wrapper())
    assert controller.update_quickly.get() > 1
    assert controller.update_once.get() == 1
    assert controller.update_never.get() == 0

    assert len(fastcs._scan_tasks) == 1
    assert len(fastcs._initial_coros) == 2


def test_scan_raises_exception_via_callback():
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

    async def test_scan_wrapper():
        await fastcs.serve_routines()
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

    loop.run_until_complete(test_scan_wrapper())
