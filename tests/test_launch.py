import json
import os
from dataclasses import dataclass

import pytest
from pydantic import create_model
from pytest_mock import MockerFixture
from ruamel.yaml import YAML
from typer.testing import CliRunner

from fastcs import __version__
from fastcs.attributes import AttrR
from fastcs.controller import Controller
from fastcs.datatypes import Int
from fastcs.exceptions import LaunchError
from fastcs.launch import TransportOptions, _launch, get_controller_schema, launch


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
        "fastcs.transport.adapter.TransportAdapter.context",
        new_callable=mocker.PropertyMock,
        return_value={"controller": "test"},
    )
    app = _launch(IsHinted)
    result = runner.invoke(app, ["run", str(data / "config.yaml")])
    assert isinstance(result.exception, RuntimeError)
    assert "Duplicate context keys found" in result.exception.args[0]
