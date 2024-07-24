import asyncio
from collections import defaultdict
from collections.abc import Callable
from types import MethodType

from .attributes import AttrR, AttrW, Sender, Updater
from .exceptions import FastCSException
from .mapping import Mapping, SingleMapping


def _get_initial_tasks(mapping: Mapping) -> list[Callable]:
    initial_tasks: list[Callable] = []
    initial_tasks.append(mapping.controller.connect)
    return initial_tasks


def _create_periodic_scan_task(period, methods: list[Callable]) -> Callable:
    async def scan_task() -> None:
        while True:
            await asyncio.gather(*[method() for method in methods])
            await asyncio.sleep(period)

    return scan_task


def _get_periodic_scan_tasks(scan_dict: dict[float, list[Callable]]) -> list[Callable]:
    periodic_scan_tasks: list[Callable] = []
    for period, methods in scan_dict.items():
        periodic_scan_tasks.append(_create_periodic_scan_task(period, methods))

    return periodic_scan_tasks


def _add_scan_method_tasks(
    scan_dict: dict[float, list[Callable]], single_mapping: SingleMapping
):
    for method in single_mapping.scan_methods.values():
        scan_dict[method.period].append(
            MethodType(method.fn, single_mapping.controller)
        )


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


def _add_attribute_updater_tasks(
    scan_dict: dict[float, list[Callable]], single_mapping: SingleMapping
):
    for attribute in single_mapping.attributes.values():
        match attribute:
            case AttrR(updater=Updater(update_period=update_period)) as attribute:
                callback = _create_updater_callback(
                    attribute, single_mapping.controller
                )
                scan_dict[update_period].append(callback)


def _get_scan_tasks(mapping: Mapping) -> list[Callable]:
    scan_dict: dict[float, list[Callable]] = defaultdict(list)

    for single_mapping in mapping.get_controller_mappings():
        _add_scan_method_tasks(scan_dict, single_mapping)
        _add_attribute_updater_tasks(scan_dict, single_mapping)

    scan_tasks = _get_periodic_scan_tasks(scan_dict)
    return scan_tasks


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


def _create_sender_callback(attribute, controller):
    async def callback(value):
        await attribute.sender.put(controller, attribute, value)

    return callback


def _link_attribute_sender_class(single_mapping: SingleMapping) -> None:
    for attr_name, attribute in single_mapping.attributes.items():
        match attribute:
            case AttrW(sender=Sender()):
                assert (
                    not attribute.has_process_callback()
                ), f"Cannot assign both put method and Sender object to {attr_name}"

                callback = _create_sender_callback(attribute, single_mapping.controller)
                attribute.set_process_callback(callback)


class Backend:
    def __init__(self, mapping: Mapping, loop: asyncio.AbstractEventLoop):
        self._mapping = mapping
        self._loop = loop

    def link_process_tasks(self):
        for single_mapping in self._mapping.get_controller_mappings():
            _link_single_controller_put_tasks(single_mapping)
            _link_attribute_sender_class(single_mapping)

    def run_initial_tasks(self):
        initial_tasks = _get_initial_tasks(self._mapping)

        for task in initial_tasks:
            future = asyncio.run_coroutine_threadsafe(task(), self._loop)
            future.result()

    def start_scan_tasks(self):
        scan_tasks = _get_scan_tasks(self._mapping)

        for task in scan_tasks:
            asyncio.run_coroutine_threadsafe(task(), self._loop)
