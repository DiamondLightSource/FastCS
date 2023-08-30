import asyncio
from collections import defaultdict
from typing import Callable, cast

from .attributes import AttrCallback, AttrMode, AttrR, AttrW
from .cs_methods import MethodType
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


def _add_wrapped_scan_tasks(
    scan_dict: dict[float, list[Callable]], single_mapping: SingleMapping
):
    for method_data in single_mapping.methods:
        if method_data.info.method_type == MethodType.scan:
            period = method_data.info.kwargs["period"]
            method = method_data.method
            scan_dict[period].append(method)


def _create_updater_callback(attribute, controller):
    async def callback():
        await attribute.updater.update(controller, attribute)

    return callback


def _add_updater_scan_tasks(
    scan_dict: dict[float, list[Callable]], single_mapping: SingleMapping
):
    for attribute in single_mapping.attributes.values():
        if attribute.access_mode in (AttrMode.READ, AttrMode.READ_WRITE):
            attribute = cast(AttrR, attribute)

            if attribute.updater is None:
                continue

            callback = _create_updater_callback(attribute, single_mapping.controller)
            scan_dict[attribute.updater.update_period].append(callback)


def _get_scan_tasks(mapping: Mapping) -> list[Callable]:
    scan_dict: dict[float, list[Callable]] = defaultdict(list)

    for single_mapping in mapping.get_controller_mappings():
        _add_wrapped_scan_tasks(scan_dict, single_mapping)
        _add_updater_scan_tasks(scan_dict, single_mapping)

    scan_tasks = _get_periodic_scan_tasks(scan_dict)
    return scan_tasks


def _link_single_controller_put_tasks(single_mapping: SingleMapping):
    put_methods = [
        method_data
        for method_data in single_mapping.methods
        if method_data.info.method_type == MethodType.put
    ]

    for method_data in put_methods:
        method = cast(AttrCallback, method_data.method)
        name = method_data.name.removeprefix("put_")

        attribute = single_mapping.attributes[name]
        assert attribute.access_mode in [
            AttrMode.WRITE,
            AttrMode.READ_WRITE,
        ], f"Mode {attribute.access_mode} does not support put operations for {name}"
        attribute = cast(AttrW, attribute)

        attribute.set_process_callback(method)


def _create_sender_callback(attribute, controller):
    async def callback(value):
        await attribute.sender.put(controller, attribute, value)

    return callback


def _link_attribute_sender_class(single_mapping: SingleMapping) -> None:
    for attr_name, attribute in single_mapping.attributes.items():
        if attribute.access_mode in (AttrMode.WRITE, AttrMode.READ_WRITE):
            attribute = cast(AttrW, attribute)

            if attribute.sender is None:
                continue

            assert (
                not attribute.has_process_callback()
            ), f"Cannot assign put method and Sender to {attr_name}"

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
