import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from concurrent.futures import Future

from softioc.asyncio_dispatcher import AsyncioDispatcher

from fastcs.datatypes import T

from .attributes import AttrR, AttrW, Sender, Updater
from .controller import BaseController, Controller
from .exceptions import FastCSException
from .mapping import Mapping, SingleMapping

Callback = Callable[[], Coroutine[None, None, None]]


class Backend:
    def __init__(
        self, controller: Controller, loop: asyncio.AbstractEventLoop | None = None
    ):
        self._dispatcher = AsyncioDispatcher(loop)
        self._loop: asyncio.AbstractEventLoop = self._dispatcher.loop  # type: ignore
        self._controller = controller

        self._initial_tasks = [controller.connect]
        self._scan_tasks: list[Future] = []

        asyncio.run_coroutine_threadsafe(
            self._controller.initialise(), self._loop
        ).result()

        self._mapping = Mapping(self._controller)
        self._link_process_tasks()

        self._context = {
            "dispatcher": self._dispatcher,
            "controller": self._controller,
            "mapping": self._mapping,
        }

    def _link_process_tasks(self):
        for single_mapping in self._mapping.get_controller_mappings():
            _link_single_controller_put_tasks(single_mapping)
            _link_attribute_sender_class(single_mapping)

    def run(self):
        self._run_initial_tasks()
        self._start_scan_tasks()

        self._run()

    def _run_initial_tasks(self):
        for task in self._initial_tasks:
            future = asyncio.run_coroutine_threadsafe(task(), self._loop)
            future.result()

    def _start_scan_tasks(self):
        scan_tasks = _get_scan_tasks(self._mapping)

        for task in scan_tasks:
            asyncio.run_coroutine_threadsafe(task(), self._loop)

    def _run(self) -> None:
        raise NotImplementedError("Specific Backend must implement _run")


def _link_single_controller_put_tasks(
    single_mapping: SingleMapping,
) -> None:
    for name, put in single_mapping.put_methods.items():
        name = name.removeprefix("put_")

        attribute = single_mapping.attributes[name]
        match attribute:
            case AttrW():
                attribute.set_process_callback(put)
            case _:
                raise FastCSException(
                    f"Mode {attribute.access_mode} does not "
                    f"support put operations for {name}"
                )


def _link_attribute_sender_class(single_mapping: SingleMapping) -> None:
    for attr_name, attribute in single_mapping.attributes.items():
        match attribute:
            case AttrW(sender=Sender()):
                assert (
                    not attribute.has_process_callback()
                ), f"Cannot assign both put method and Sender object to {attr_name}"

                callback = _create_sender_callback(attribute, single_mapping.controller)
                attribute.set_process_callback(callback)
            case _:
                pass


def _create_sender_callback(
    attribute: AttrW[T], controller: BaseController
) -> Callable[[T], Coroutine[None, None, None]]:
    match attribute.sender:
        case Sender() as sender:

            async def put_callback(value: T):
                await sender.put(controller, attribute, value)
        case _:

            async def put_callback(value: T):
                pass

    return put_callback


def _get_scan_tasks(mapping: Mapping) -> list[Callback]:
    scan_dict: dict[float, list[Callback]] = defaultdict(list)

    for single_mapping in mapping.get_controller_mappings():
        _add_scan_method_tasks(scan_dict, single_mapping)
        _add_attribute_updater_tasks(scan_dict, single_mapping)

    scan_tasks = _get_periodic_scan_tasks(scan_dict)
    return scan_tasks


def _add_scan_method_tasks(
    scan_dict: dict[float, list[Callback]], single_mapping: SingleMapping
):
    for scan in single_mapping.scan_methods.values():
        scan_dict[scan.period].append(scan)


def _add_attribute_updater_tasks(
    scan_dict: dict[float, list[Callback]],
    single_mapping: SingleMapping,
):
    for attribute in single_mapping.attributes.values():
        match attribute:
            case AttrR(updater=Updater(update_period=update_period)) as attribute:
                callback = _create_updater_callback(
                    attribute, single_mapping.controller
                )
                scan_dict[update_period].append(callback)
            case _:
                pass


def _create_updater_callback(
    attribute: AttrR[T], controller: BaseController
) -> Callback:
    async def callback():
        try:
            match attribute.updater:
                case Updater() as updater:
                    await updater.update(controller, attribute)
                case _:
                    pass
        except Exception as e:
            print(
                f"Update loop in {attribute.updater} stopped:\n"
                f"{e.__class__.__name__}: {e}"
            )
            raise

    return callback


def _get_periodic_scan_tasks(scan_dict: dict[float, list[Callback]]) -> list[Callback]:
    periodic_scan_tasks: list[Callback] = []
    for period, methods in scan_dict.items():
        periodic_scan_tasks.append(_create_periodic_scan_task(period, methods))

    return periodic_scan_tasks


def _create_periodic_scan_task(period: float, methods: list[Callback]) -> Callback:
    async def scan_task() -> None:
        while True:
            await asyncio.gather(*[method() for method in methods])
            await asyncio.sleep(period)

    return scan_task
