import asyncio
import signal
from collections.abc import Coroutine, Sequence
from functools import partial
from typing import Any

from IPython.terminal.embed import InteractiveShellEmbed

from fastcs.controller import BaseController, Controller
from fastcs.controller_api import ControllerAPI
from fastcs.cs_methods import Command, Scan, ScanCallback
from fastcs.exceptions import FastCSError
from fastcs.logging import logger as _fastcs_logger
from fastcs.tracer import Tracer
from fastcs.transport import Transport
from fastcs.util import validate_hinted_attributes

tracer = Tracer(name=__name__)
logger = _fastcs_logger.bind(logger_name=__name__)


class FastCS:
    """Entrypoint for a FastCS application.

    This class takes a ``Controller``, creates asyncio tasks to run its update loops and
    builds its API to serve over the given transports.

    :param: controller: The controller to serve in the control system
    :param: transports: A list of transports to serve the API over
    :param: loop: Optional event loop to run the control system in
    """

    def __init__(
        self,
        controller: Controller,
        transports: Sequence[Transport],
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self._controller = controller
        self._transports = transports
        self._loop = loop or asyncio.get_event_loop()

        self._scan_coros: list[ScanCallback] = []
        self._initial_coros: list[ScanCallback] = []

        self._scan_tasks: set[asyncio.Task] = set()

    def run(self, interactive: bool = True):
        serve = asyncio.ensure_future(self.serve(interactive=interactive))

        self._loop.add_signal_handler(signal.SIGINT, serve.cancel)
        self._loop.add_signal_handler(signal.SIGTERM, serve.cancel)
        self._loop.run_until_complete(serve)

    async def _run_initial_coros(self):
        for coro in self._initial_coros:
            await coro()

    async def _start_scan_tasks(self):
        self._scan_tasks = {self._loop.create_task(coro()) for coro in self._scan_coros}

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
                except (asyncio.CancelledError, RuntimeError):
                    pass
                except Exception as e:
                    raise RuntimeError("Unhandled exception in stop scan tasks") from e

        self._scan_tasks.clear()

    async def serve(self, interactive: bool = True) -> None:
        await self._controller.initialise()
        validate_hinted_attributes(self._controller)
        self._controller.connect_attribute_ios()

        self.controller_api = build_controller_api(self._controller)
        self._scan_coros, self._initial_coros = (
            self.controller_api.get_scan_and_initial_coros()
        )

        context = {
            "controller": self._controller,
            "controller_api": self.controller_api,
            "transports": [
                transport.__class__.__name__ for transport in self._transports
            ],
        }

        coros: list[Coroutine] = []
        for transport in self._transports:
            transport.connect(controller_api=self.controller_api, loop=self._loop)
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

        if interactive:
            coros.append(self._interactive_shell(context))
        else:

            async def block_forever():
                while True:
                    await asyncio.sleep(1)

            coros.append(block_forever())

        logger.info(
            "Starting FastCS",
            controller=self._controller,
            transports=f"[{', '.join(str(t) for t in self._transports)}]",
        )

        await self._controller.connect()
        await self._run_initial_coros()
        await self._start_scan_tasks()

        try:
            await asyncio.gather(*coros)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Unhandled exception in serve")
        finally:
            logger.info("Shutting down FastCS")
            self._stop_scan_tasks()
            await self._controller.disconnect()

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

    def __del__(self):
        self._stop_scan_tasks()


def build_controller_api(controller: Controller) -> ControllerAPI:
    return _build_controller_api(controller, [])


def _build_controller_api(controller: BaseController, path: list[str]) -> ControllerAPI:
    scan_methods: dict[str, Scan] = {}
    command_methods: dict[str, Command] = {}
    for attr_name in dir(controller):
        attr = getattr(controller, attr_name)
        match attr:
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
        command_methods=command_methods,
        sub_apis={
            name: _build_controller_api(sub_controller, path + [name])
            for name, sub_controller in controller.sub_controllers.items()
        },
        description=controller.description,
    )
