import json
from dataclasses import dataclass

import pytest
from pydantic import create_model
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from fastcs.__main__ import __version__
from fastcs.controller import Controller
from fastcs.exceptions import LaunchError
from fastcs.launch import TransportOptions, _launch, launch


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
    def __init__(self, arg: SomeConfig) -> None:
        super().__init__()


class ManyArgs(Controller):
    def __init__(self, arg: SomeConfig, too_many):
        super().__init__()


runner = CliRunner()


def test_single_arg_schema():
    target_model = create_model(
        "SingleArg",
        transport=(TransportOptions, ...),
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
        transport=(TransportOptions, ...),
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
        "but received 3 as `(self, arg: test_launch.SomeConfig, too_many)`"
    )

    with pytest.raises(LaunchError) as exc_info:
        launch(ManyArgs)
    assert str(exc_info.value) == error


def test_version():
    impl_version = "0.0.1"
    expected = f"SingleArg: {impl_version}\n" f"FastCS: {__version__}\n"
    app = _launch(SingleArg, version=impl_version)
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout == expected


def test_no_version():
    expected = f"FastCS: {__version__}\n"
    app = _launch(SingleArg)
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout == expected


def test_launch_minimal(mocker: MockerFixture, data):
    run = mocker.patch("fastcs.launch.FastCS.run")
    gui = mocker.patch("fastcs.launch.FastCS.create_gui")
    docs = mocker.patch("fastcs.launch.FastCS.create_docs")

    app = _launch(SingleArg)
    result = runner.invoke(app, ["run", str(data / "config_minimal.yaml")])
    assert result.exit_code == 0

    run.assert_called_once()
    gui.assert_not_called()
    docs.assert_not_called()


def test_launch_full(mocker: MockerFixture, data):
    run = mocker.patch("fastcs.launch.FastCS.run")
    gui = mocker.patch("fastcs.launch.FastCS.create_gui")
    docs = mocker.patch("fastcs.launch.FastCS.create_docs")

    app = _launch(IsHinted)
    result = runner.invoke(app, ["run", str(data / "config_full.yaml")])
    assert result.exit_code == 0

    run.assert_called_once()
    gui.assert_called_once()
    docs.assert_called_once()
