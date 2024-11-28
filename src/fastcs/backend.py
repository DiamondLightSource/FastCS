import asyncio
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import Future
from types import MethodType

from softioc.asyncio_dispatcher import AsyncioDispatcher

from .attributes import AttrR, AttrW, Sender, Updater
from .controller import Controller, SingleMapping
from .exceptions import FastCSException


class Backend:
    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self.dispatcher = AsyncioDispatcher(loop)
        self._loop = self.dispatcher.loop
        self._controller = controller

        self._initial_coros = [controller.connect]
        self._scan_futures: set[Future] = set()

        asyncio.run_coroutine_threadsafe(
            self._controller.initialise(), self._loop
        ).result()

        self._link_process_tasks()

    def _link_process_tasks(self):
        for single_mapping in self._controller.get_controller_mappings():
            _link_single_controller_put_tasks(single_mapping)
            _link_attribute_sender_class(single_mapping)

    def __del__(self):
        self.stop_scan_futures()

    def run(self):
        self._run_initial_futures()
        self.start_scan_futures()

    def _run_initial_futures(self):
        for coro in self._initial_coros:
            future = asyncio.run_coroutine_threadsafe(coro(), self._loop)
            future.result()

    def start_scan_futures(self):
        self._scan_futures = {
            asyncio.run_coroutine_threadsafe(coro(), self._loop)
            for coro in _get_scan_coros(self._controller)
        }

    def stop_scan_futures(self):
        for future in self._scan_futures:
            if not future.done():
                try:
                    future.cancel()
                except asyncio.CancelledError:
                    pass


def _link_single_controller_put_tasks(single_mapping: SingleMapping) -> None:
    for name, method in single_mapping.put_methods.items():
        name = name.removeprefix("put_")

        attribute = single_mapping.attributes[name]
        match attribute:
            case AttrW():
                attribute.set_process_callback(
                    MethodType(method.fn, single_mapping.controller)
                )
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


def _create_sender_callback(attribute, controller):
    async def callback(value):
        await attribute.sender.put(controller, attribute, value)

    return callback


def _get_scan_coros(controller: Controller) -> list[Callable]:
    scan_dict: dict[float, list[Callable]] = defaultdict(list)

    for single_mapping in controller.get_controller_mappings():
        _add_scan_method_tasks(scan_dict, single_mapping)
        _add_attribute_updater_tasks(scan_dict, single_mapping)

    scan_coros = _get_periodic_scan_coros(scan_dict)
    return scan_coros


def _add_scan_method_tasks(
    scan_dict: dict[float, list[Callable]], single_mapping: SingleMapping
):
    for method in single_mapping.scan_methods.values():
        scan_dict[method.period].append(
            MethodType(method.fn, single_mapping.controller)
        )


def _add_attribute_updater_tasks(
    scan_dict: dict[float, list[Callable]], single_mapping: SingleMapping
):
    for attribute in single_mapping.attributes.values():
        match attribute:
            case AttrR(updater=Updater(update_period=update_period)) as attribute:
                callback = _create_updater_callback(
                    attribute, single_mapping.controller
                )
                if update_period is not None:
                    scan_dict[update_period].append(callback)


def _create_updater_callback(attribute, controller):
    async def callback():
        try:
            await attribute.updater.update(controller, attribute)
        except Exception as e:
            print(
                f"Update loop in {attribute.updater} stopped:\n"
                f"{e.__class__.__name__}: {e}"
            )
            raise

    return callback


def _get_periodic_scan_coros(scan_dict: dict[float, list[Callable]]) -> list[Callable]:
    periodic_scan_coros: list[Callable] = []
    for period, methods in scan_dict.items():
        periodic_scan_coros.append(_create_periodic_scan_coro(period, methods))

    return periodic_scan_coros


def _create_periodic_scan_coro(period, methods: list[Callable]) -> Callable:
    async def scan_coro() -> None:
        while True:
            await asyncio.gather(*[method() for method in methods])
            await asyncio.sleep(period)

    return scan_coro
