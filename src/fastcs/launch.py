import asyncio
import inspect
import json
from pathlib import Path
from typing import Annotated, TypeAlias, get_type_hints

import typer
from pydantic import BaseModel, create_model
from ruamel.yaml import YAML

from .backend import Backend
from .controller import Controller
from .exceptions import LaunchError
from .transport.adapter import TransportAdapter
from .transport.epics.options import EpicsOptions
from .transport.rest.options import RestOptions
from .transport.tango.options import TangoOptions

# Define a type alias for transport options
TransportOptions: TypeAlias = list[EpicsOptions | TangoOptions | RestOptions]


class FastCS:
    def __init__(
        self,
        controller: Controller,
        transport_options: TransportOptions,
    ):
        self._loop = asyncio.get_event_loop()
        self._backend = Backend(controller, self._loop)
        transport: TransportAdapter
        self._transports: list[TransportAdapter] = []
        for option in transport_options:
            match option:
                case EpicsOptions():
                    from .transport.epics.adapter import EpicsTransport

                    transport = EpicsTransport(
                        controller,
                        self._loop,
                        option,
                    )
                case TangoOptions():
                    from .transport.tango.adapter import TangoTransport

                    transport = TangoTransport(
                        controller,
                        self._loop,
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

    def run(self):
        self._loop.run_until_complete(
            self.serve(),
        )

    async def serve(self) -> None:
        coros = [self._backend.run()]
        coros.extend([transport.run() for transport in self._transports])
        await asyncio.gather(*coros)


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
            transport=(TransportOptions, ...),
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
            transport=(TransportOptions, ...),
            __config__={"extra": "forbid"},
        )
    else:
        raise LaunchError(
            f"Expected no more than 2 arguments for '{controller_class.__name__}"
            f".__init__' but received {len(args)} as `{sig}`"
        )
    return fastcs_options