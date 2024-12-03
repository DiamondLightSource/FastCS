import inspect
import json
import threading
from pathlib import Path
from typing import Annotated, get_type_hints

import typer
from pydantic import BaseModel, create_model
from ruamel.yaml import YAML

from .backend import Backend
from .controller import Controller
from .exceptions import LaunchError
from .transport.adapter import TransportAdapter, TransportOptions
from .transport.epics.options import EpicsOptions
from .transport.rest.options import RestOptions
from .transport.tango.options import TangoOptions


class FastCS:
    def __init__(
        self,
        controller: Controller,
        transport_options: list[TransportOptions],
    ):
        self._backend = Backend(controller)
        self._transport_threads: list[threading.Thread] = []
        self._transports: list[TransportAdapter] = []
        option: TransportOptions
        transport: TransportAdapter
        for option in transport_options:
            match option:
                case EpicsOptions():
                    from .transport.epics.adapter import EpicsTransport

                    transport = EpicsTransport(
                        controller,
                        self._backend.dispatcher,
                        option,
                    )
                case TangoOptions():
                    from .transport.tango.adapter import TangoTransport

                    transport = TangoTransport(
                        controller,
                        option,
                    )
                case RestOptions():
                    from .transport.rest.adapter import RestTransport

                    transport = RestTransport(
                        controller,
                        option,
                    )

            self._transports.append(transport)

    def create_docs(self) -> None:
        for transport in self._transports:
            if hasattr(transport.options, "docs"):
                transport.create_docs()

    def create_gui(self) -> None:
        for transport in self._transports:
            if hasattr(transport.options, "gui"):
                transport.create_docs()

    def run(self) -> None:
        self._backend.run()
        for transport in self._transports:
            self._transport_threads.append(threading.Thread(target=transport.run))
            self._transport_threads[-1].start()

        for thread in self._transport_threads:
            thread.join()


def launch(controller_class: type[Controller]) -> None:
    """
    Serves as an entry point for starting FastCS applications.
    By utilizing type hints in a Controller's __init__ method, this
    function provides a command-line interface to describe and gather the
    required configuration before instantiating the application.
    Args:
        controller_class (type[Controller]): The FastCS Controller to instantiate.
        It must have a type-hinted __init__ method and no more than 2 arguments.
    Raises:
        LaunchError: If the class's __init__ is not as expected
    Example of the expected Controller implementation:
        class MyController(Controller):
            def __init__(self, my_arg: MyControllerOptions) -> None:
                ...
    Typical usage:
        if __name__ == "__main__":
            launch(MyController)
    """
    _launch(controller_class)()


def _launch(controller_class: type[Controller]) -> typer.Typer:
    fastcs_options = _extract_options_model(controller_class)
    launch_typer = typer.Typer()

    class LaunchContext:
        def __init__(self, controller_class, fastcs_options):
            self.controller_class = controller_class
            self.fastcs_options = fastcs_options

    @launch_typer.callback()
    def create_context(ctx: typer.Context):
        ctx.obj = LaunchContext(
            controller_class,
            fastcs_options,
        )

    @launch_typer.command(help=f"Produce json schema for a {controller_class.__name__}")
    def schema(ctx: typer.Context):
        system_schema = ctx.obj.fastcs_options.model_json_schema()
        print(json.dumps(system_schema, indent=2))

    @launch_typer.command(help=f"Start up a {controller_class.__name__}")
    def run(
        ctx: typer.Context,
        config: Annotated[
            Path,
            typer.Argument(
                help=f"A yaml file matching the {controller_class.__name__} schema"
            ),
        ],
    ):
        """
        Start the controller
        """
        controller_class = ctx.obj.controller_class
        fastcs_options = ctx.obj.fastcs_options

        yaml = YAML(typ="safe")
        options_yaml = yaml.load(config)
        # To do: Handle a k8s "values.yaml" file
        instance_options = fastcs_options.model_validate(options_yaml)
        if hasattr(instance_options, "controller"):
            controller = controller_class(instance_options.controller)
        else:
            controller = controller_class()

        instance = FastCS(
            controller,
            instance_options.transport,
        )

        instance.create_gui()
        instance.create_docs()
        instance.run()

    return launch_typer


def _extract_options_model(controller_class: type[Controller]) -> type[BaseModel]:
    sig = inspect.signature(controller_class.__init__)
    args = inspect.getfullargspec(controller_class.__init__)[0]
    if len(args) == 1:
        fastcs_options = create_model(
            f"{controller_class.__name__}",
            transport=(list[TransportOptions], ...),
            __config__={"extra": "forbid"},
        )
    elif len(args) == 2:
        hints = get_type_hints(controller_class.__init__)
        if hints:
            options_type = list(hints.values())[-1]
        else:
            raise LaunchError(
                f"Expected typehinting in '{controller_class.__name__}"
                f".__init__' but received {sig}. Add a typehint for `{args[-1]}`."
            )
        fastcs_options = create_model(
            f"{controller_class.__name__}",
            controller=(options_type, ...),
            transport=(list[TransportOptions], ...),
            __config__={"extra": "forbid"},
        )
    else:
        raise LaunchError(
            f"Expected no more than 2 arguments for '{controller_class.__name__}"
            f".__init__' but received {len(args)} as `{sig}`"
        )
    return fastcs_options
