import asyncio
from collections import defaultdict
from collections.abc import Callable

from fastcs.cs_methods import Command, Put, Scan
from fastcs.datatypes import T

from .attributes import AttrHandlerR, AttrHandlerW, AttrR, AttrW
from .controller import BaseController, Controller
from .controller_api import ControllerAPI
from .exceptions import FastCSException


class Backend:
    """For keeping track of tasks during FastCS serving."""

    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop,
    ):
        self._controller = controller
        self._loop = loop

        self._initial_coros = [controller.connect]
        self._scan_tasks: set[asyncio.Task] = set()

        # Initialise controller and then build its APIs
        loop.run_until_complete(controller.initialise())
        loop.run_until_complete(controller.attribute_initialise())
        self.controller_api = build_controller_api(controller)
        self._link_process_tasks()

    def _link_process_tasks(self):
        for controller_api in self.controller_api.walk_api():
            _link_put_tasks(controller_api)
            _link_attribute_sender_class(controller_api)

    def __del__(self):
        self._stop_scan_tasks()

    async def serve(self):
        await self._run_initial_coros()
        await self._start_scan_tasks()

    async def _run_initial_coros(self):
        for coro in self._initial_coros:
            await coro()

    async def _start_scan_tasks(self):
        self._scan_tasks = {
            self._loop.create_task(coro())
            for coro in _get_scan_coros(self.controller_api)
        }

    def _stop_scan_tasks(self):
        for task in self._scan_tasks:
            if not task.done():
                try:
                    task.cancel()
                except asyncio.CancelledError:
                    pass


def _link_put_tasks(controller_api: ControllerAPI) -> None:
    for name, method in controller_api.put_methods.items():
        name = name.removeprefix("put_")

        attribute = controller_api.attributes[name]
        match attribute:
            case AttrW():
                attribute.add_process_callback(method.fn)
            case _:
                raise FastCSException(
                    f"Mode {attribute.access_mode} does not "
                    f"support put operations for {name}"
                )


def _link_attribute_sender_class(controller_api: ControllerAPI) -> None:
    for attr_name, attribute in controller_api.attributes.items():
        match attribute:
            case AttrW(sender=AttrHandlerW()):
                assert not attribute.has_process_callback(), (
                    f"Cannot assign both put method and Sender object to {attr_name}"
                )

                callback = _create_sender_callback(attribute)
                attribute.add_process_callback(callback)


def _create_sender_callback(attribute):
    async def callback(value):
        await attribute.sender.put(attribute, value)

    return callback


def _get_scan_coros(root_controller_api: ControllerAPI) -> list[Callable]:
    scan_dict: dict[float, list[Callable]] = defaultdict(list)

    for controller_api in root_controller_api.walk_api():
        _add_scan_method_tasks(scan_dict, controller_api)
        _add_attribute_updater_tasks(scan_dict, controller_api)

    scan_coros = _get_periodic_scan_coros(scan_dict)
    return scan_coros


def _add_scan_method_tasks(
    scan_dict: dict[float, list[Callable]], controller_api: ControllerAPI
):
    for method in controller_api.scan_methods.values():
        scan_dict[method.period].append(method.fn)


def _add_attribute_updater_tasks(
    scan_dict: dict[float, list[Callable]], controller_api: ControllerAPI
):
    for attribute in controller_api.attributes.values():
        match attribute:
            case AttrR(updater=AttrHandlerR(update_period=update_period)) as attribute:
                callback = _create_updater_callback(attribute)
                if update_period is not None:
                    scan_dict[update_period].append(callback)


def _create_updater_callback(attribute: AttrR[T]):
    updater = attribute.updater
    assert updater is not None

    async def callback():
        try:
            await updater.update(attribute)
        except Exception as e:
            print(f"Update loop in {updater} stopped:\n{e.__class__.__name__}: {e}")
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
    """Build a `ControllerAPI` for a `BaseController` and its sub controllers"""
    return _build_controller_api(controller, [])


def _build_controller_api(controller: BaseController, path: list[str]) -> ControllerAPI:
    """Build a `ControllerAPI` for a `BaseController` and its sub controllers"""
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
        command_methods=command_methods,
        put_methods=put_methods,
        scan_methods=scan_methods,
        sub_apis={
            name: _build_controller_api(sub_controller, path + [name])
            for name, sub_controller in controller.get_sub_controllers().items()
        },
        description=controller.description,
    )
