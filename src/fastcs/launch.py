import asyncio
import inspect
import json
import signal
from collections.abc import Coroutine
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Optional, TypeAlias, get_type_hints

import typer
from IPython.terminal.embed import InteractiveShellEmbed
from pydantic import BaseModel, create_model
from ruamel.yaml import YAML

from fastcs import __version__

from .backend import Backend
from .controller import Controller
from .exceptions import LaunchError
from .transport.adapter import TransportAdapter
from .transport.epics.ca.options import EpicsCAOptions
from .transport.epics.pva.options import EpicsPVAOptions
from .transport.graphQL.options import GraphQLOptions
from .transport.rest.options import RestOptions
from .transport.tango.options import TangoOptions

# Define a type alias for transport options
TransportOptions: TypeAlias = list[
    EpicsPVAOptions | EpicsCAOptions | TangoOptions | RestOptions | GraphQLOptions
]


class FastCS:
    """For launching a controller with given transport(s)."""

    def __init__(
        self,
        controller: Controller,
        transport_options: TransportOptions,
    ):
        self._loop = asyncio.get_event_loop()
        self._controller = controller
        self._backend = Backend(controller, self._loop)
        transport: TransportAdapter
        self._transports: list[TransportAdapter] = []
        for option in transport_options:
            match option:
                case EpicsPVAOptions():
                    from .transport.epics.pva.adapter import EpicsPVATransport

                    transport = EpicsPVATransport(
                        self._backend.controller_api,
                        option,
                    )
                case EpicsCAOptions():
                    from .transport.epics.ca.adapter import EpicsCATransport

                    transport = EpicsCATransport(
                        self._backend.controller_api,
                        self._loop,
                        option,
                    )
                case TangoOptions():
                    from .transport.tango.adapter import TangoTransport

                    transport = TangoTransport(
                        self._backend.controller_api,
                        self._loop,
                        option,
                    )
                case RestOptions():
                    from .transport.rest.adapter import RestTransport

                    transport = RestTransport(
                        self._backend.controller_api,
                        option,
                    )
                case GraphQLOptions():
                    from .transport.graphQL.adapter import GraphQLTransport

                    transport = GraphQLTransport(
                        self._backend.controller_api,
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
                transport.create_gui()

    def run(self):
        serve = asyncio.ensure_future(self.serve())

        self._loop.add_signal_handler(signal.SIGINT, serve.cancel)
        self._loop.add_signal_handler(signal.SIGTERM, serve.cancel)
        self._loop.run_until_complete(serve)

    async def serve(self) -> None:
        coros = [self._backend.serve()]
        context = {
            "controller": self._controller,
            "controller_api": self._backend.controller_api,
            "transports": [
                transport.__class__.__name__ for transport in self._transports
            ],
        }

        for transport in self._transports:
            coros.append(transport.serve())
            common_context = context.keys() & transport.context.keys()
            if common_context:
                raise RuntimeError(
                    "Duplicate context keys found between "
                    f"current context { ({k: context[k] for k in common_context}) } "
                    f"and {transport.__class__.__name__} context: "
                    f"{ ({k: transport.context[k] for k in common_context}) }"
                )
            context.update(transport.context)

        coros.append(self._interactive_shell(context))

        try:
            await asyncio.gather(*coros)
        except asyncio.CancelledError:
            pass

    async def _interactive_shell(self, context: dict[str, Any]):
        """Spawn interactive shell in another thread and wait for it to complete."""

        def run(coro: Coroutine[None, None, None]):
            """Run coroutine on FastCS event loop from IPython thread."""

            def wrapper():
                asyncio.create_task(coro)

            self._loop.call_soon_threadsafe(wrapper)

        async def interactive_shell(
            context: dict[str, object], stop_event: asyncio.Event
        ):
            """Run interactive shell in a new thread."""
            shell = InteractiveShellEmbed()
            await asyncio.to_thread(partial(shell.mainloop, local_ns=context))

            stop_event.set()

        context["run"] = run

        stop_event = asyncio.Event()
        self._loop.create_task(interactive_shell(context, stop_event))
        await stop_event.wait()


def launch(
    controller_class: type[Controller],
    version: str | None = None,
) -> None:
    """
    Serves as an entry point for starting FastCS applications.

    By utilizing type hints in a Controller's __init__ method, this
    function provides a command-line interface to describe and gather the
    required configuration before instantiating the application.

    Args:
        controller_class (type[Controller]): The FastCS Controller to instantiate.
            It must have a type-hinted __init__ method and no more than 2 arguments.
        version (Optional[str]): The version of the FastCS Controller.
            Optional

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
    _launch(controller_class, version)()


def _launch(
    controller_class: type[Controller],
    version: str | None = None,
) -> typer.Typer:
    fastcs_options = _extract_options_model(controller_class)
    launch_typer = typer.Typer()

    class LaunchContext:
        def __init__(self, controller_class, fastcs_options):
            self.controller_class = controller_class
            self.fastcs_options = fastcs_options

    def version_callback(value: bool):
        if value:
            if version:
                print(f"{controller_class.__name__}: {version}")
            print(f"FastCS: {__version__}")
            raise typer.Exit()

    @launch_typer.callback()
    def main(
        ctx: typer.Context,
        version: Optional[bool] = typer.Option(  # noqa (Optional required for typer)
            None,
            "--version",
            callback=version_callback,
            is_eager=True,
            help=f"Display the {controller_class.__name__} version.",
        ),
    ):
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
        if "return" in hints:
            del hints["return"]
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


def get_controller_schema(target: type[Controller]) -> dict[str, Any]:
    """Gets schema for a give controller for serialisation."""
    options_model = _extract_options_model(target)
    target_schema = options_model.model_json_schema()
    return target_schema
