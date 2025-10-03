import asyncio
import inspect
import json
import signal
from collections import defaultdict
from collections.abc import Callable, Coroutine, Sequence
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Optional, TypeAlias, get_type_hints

import typer
from IPython.terminal.embed import InteractiveShellEmbed
from pydantic import BaseModel, create_model
from ruamel.yaml import YAML

from fastcs import __version__
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.transport.epics.ca.transport import EpicsCATransport
from fastcs.transport.epics.pva.transport import EpicsPVATransport
from fastcs.transport.graphql.transport import GraphQLTransport
from fastcs.transport.rest.transport import RestTransport
from fastcs.transport.tango.transport import TangoTransport

from .attributes import ONCE, AttrR, AttrW
from .controller import BaseController, Controller
from .controller_api import ControllerAPI
from .cs_methods import Command, Put, Scan
from .datatypes import T
from .exceptions import FastCSError, LaunchError
from .transport import Transport
from .util import validate_hinted_attributes

# Define a type alias for transport options
TransportList: TypeAlias = list[
    EpicsPVATransport
    | EpicsCATransport
    | TangoTransport
    | RestTransport
    | GraphQLTransport
]


class FastCS:
    """For launching a controller with given transport(s) and keeping
    track of tasks during serving."""

    def __init__(
        self,
        controller: Controller,
        transports: Sequence[Transport],
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self._loop = loop or asyncio.get_event_loop()
        self._controller = controller

        self._initial_coros = [controller.connect]
        self._scan_tasks: set[asyncio.Task] = set()

        # these initialise the controller & build its APIs
        self._loop.run_until_complete(controller.initialise())
        self._loop.run_until_complete(controller.attribute_initialise())
        validate_hinted_attributes(controller)
        self.controller_api = build_controller_api(controller)
        self._link_process_tasks()

        self._transports = transports
        for transport in self._transports:
            transport.initialise(controller_api=self.controller_api, loop=self._loop)

    def create_docs(self) -> None:
        for transport in self._transports:
            transport.create_docs()

    def create_gui(self) -> None:
        for transport in self._transports:
            transport.create_gui()

    def run(self):
        serve = asyncio.ensure_future(self.serve())

        self._loop.add_signal_handler(signal.SIGINT, serve.cancel)
        self._loop.add_signal_handler(signal.SIGTERM, serve.cancel)
        self._loop.run_until_complete(serve)

    def _link_process_tasks(self):
        for controller_api in self.controller_api.walk_api():
            _link_put_tasks(controller_api)

    def __del__(self):
        self._stop_scan_tasks()

    async def serve_routines(self):
        scans, initials = _get_scan_and_initial_coros(self.controller_api)
        self._initial_coros += initials
        await self._run_initial_coros()
        await self._start_scan_tasks(scans)

    async def _run_initial_coros(self):
        for coro in self._initial_coros:
            await coro()

    async def _start_scan_tasks(
        self, coros: list[Callable[[], Coroutine[None, None, None]]]
    ):
        self._scan_tasks = {self._loop.create_task(coro()) for coro in coros}

        for task in self._scan_tasks:
            task.add_done_callback(self._scan_done)

    def _scan_done(self, task: asyncio.Task):
        try:
            task.result()
        except Exception as e:
            raise FastCSError(
                "Exception raised in scan method of "
                f"{self._controller.__class__.__name__}"
            ) from e

    def _stop_scan_tasks(self):
        for task in self._scan_tasks:
            if not task.done():
                try:
                    task.cancel()
                except asyncio.CancelledError:
                    pass

    async def serve(self) -> None:
        coros = [self.serve_routines()]

        context = {
            "controller": self._controller,
            "controller_api": self.controller_api,
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


def _link_put_tasks(controller_api: ControllerAPI) -> None:
    for name, method in controller_api.put_methods.items():
        name = name.removeprefix("put_")

        attribute = controller_api.attributes[name]
        match attribute:
            case AttrW():
                attribute.add_process_callback(method.fn)
            case _:
                raise FastCSError(
                    f"Attribute type {type(attribute)} does not"
                    f"support put operations for {name}"
                )


def _get_scan_and_initial_coros(
    root_controller_api: ControllerAPI,
) -> tuple[list[Callable], list[Callable]]:
    scan_dict: dict[float, list[Callable]] = defaultdict(list)
    initial_coros: list[Callable] = []

    for controller_api in root_controller_api.walk_api():
        _add_scan_method_tasks(scan_dict, controller_api)
        _add_attribute_updater_tasks(scan_dict, initial_coros, controller_api)

    scan_coros = _get_periodic_scan_coros(scan_dict)
    return scan_coros, initial_coros


def _add_scan_method_tasks(
    scan_dict: dict[float, list[Callable]], controller_api: ControllerAPI
):
    for method in controller_api.scan_methods.values():
        scan_dict[method.period].append(method.fn)


def _add_attribute_updater_tasks(
    scan_dict: dict[float, list[Callable]],
    initial_coros: list[Callable],
    controller_api: ControllerAPI,
):
    for attribute in controller_api.attributes.values():
        match attribute:
            case (
                AttrR(_io_ref=AttributeIORef(update_period=update_period)) as attribute
            ):
                callback = _create_updater_callback(attribute)
                if update_period is ONCE:
                    initial_coros.append(callback)
                elif update_period is not None:
                    scan_dict[update_period].append(callback)


def _create_updater_callback(attribute: AttrR[T]):
    async def callback():
        try:
            await attribute.update()
        except Exception as e:
            print(f"Update loop in {attribute} stopped:\n{e.__class__.__name__}: {e}")
            raise

    return callback


def _get_periodic_scan_coros(scan_dict: dict[float, list[Callable]]) -> list[Callable]:
    periodic_scan_coros: list[Callable] = []
    for period, methods in scan_dict.items():
        periodic_scan_coros.append(_create_periodic_scan_coro(period, methods))

    return periodic_scan_coros


def _create_periodic_scan_coro(period, methods: list[Callable]) -> Callable:
    async def _sleep():
        await asyncio.sleep(period)

    methods.append(_sleep)  # Create periodic behavior

    async def scan_coro() -> None:
        while True:
            await asyncio.gather(*[method() for method in methods])

    return scan_coro


def build_controller_api(controller: Controller) -> ControllerAPI:
    return _build_controller_api(controller, [])


def _build_controller_api(controller: BaseController, path: list[str]) -> ControllerAPI:
    scan_methods: dict[str, Scan] = {}
    put_methods: dict[str, Put] = {}
    command_methods: dict[str, Command] = {}
    for attr_name in dir(controller):
        attr = getattr(controller, attr_name)
        match attr:
            case Put(enabled=True):
                put_methods[attr_name] = attr
            case Scan(enabled=True):
                scan_methods[attr_name] = attr
            case Command(enabled=True):
                command_methods[attr_name] = attr
            case _:
                pass

    return ControllerAPI(
        path=path,
        attributes=controller.attributes,
        scan_methods=scan_methods,
        put_methods=put_methods,
        command_methods=command_methods,
        sub_apis={
            name: _build_controller_api(sub_controller, path + [name])
            for name, sub_controller in controller.get_sub_controllers().items()
        },
        description=controller.description,
    )


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
            loop=asyncio.get_event_loop(),
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
            transport=(TransportList, ...),
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
            transport=(TransportList, ...),
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
