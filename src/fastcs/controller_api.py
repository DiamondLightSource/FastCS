import asyncio
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import ONCE, Attribute, AttrR
from fastcs.cs_methods import Command, Scan, ScanCallback
from fastcs.logging import logger as _fastcs_logger
from fastcs.tracer import Tracer

tracer = Tracer(name=__name__)
logger = _fastcs_logger.bind(logger_name=__name__)


@dataclass
class ControllerAPI:
    """Attributes, bound methods and sub APIs of a `Controller`"""

    path: list[str] = field(default_factory=list)
    """Path within controller tree (empty if this is the root)"""
    attributes: dict[str, Attribute] = field(default_factory=dict)
    command_methods: dict[str, Command] = field(default_factory=dict)
    scan_methods: dict[str, Scan] = field(default_factory=dict)
    sub_apis: dict[str, "ControllerAPI"] = field(default_factory=dict)
    """APIs of the sub controllers of the `Controller` this API was built from"""
    description: str | None = None

    def walk_api(self) -> Iterator["ControllerAPI"]:
        """Walk through all the nested `ControllerAPI` s of this `ControllerAPI`.

        Yields the `ControllerAPI` s from a depth-first traversal of the tree,
        including self.

        """
        yield self
        for api in self.sub_apis.values():
            yield from api.walk_api()

    def __repr__(self):
        return (
            f"ControllerAPI("
            f"path={self.path}, "
            f"sub_apis=[{', '.join(self.sub_apis.keys())}]"
            f")"
        )

    def get_scan_and_initial_coros(
        self,
    ) -> tuple[list[ScanCallback], list[ScanCallback]]:
        scan_dict: dict[float, list[Callable]] = defaultdict(list)
        initial_coros: list[Callable] = []

        for controller_api in self.walk_api():
            _add_scan_method_tasks(scan_dict, initial_coros, controller_api)
            _add_attribute_update_tasks(scan_dict, initial_coros, controller_api)

        scan_coros = _get_periodic_scan_coros(scan_dict)
        return scan_coros, initial_coros


def _add_scan_method_tasks(
    scan_dict: dict[float, list[Callable]],
    initial_coros: list[Callable],
    controller_api: ControllerAPI,
):
    for method in controller_api.scan_methods.values():
        if method.period is ONCE:
            initial_coros.append(method.fn)
        else:
            scan_dict[method.period].append(method.fn)


def _add_attribute_update_tasks(
    scan_dict: dict[float, list[Callable]],
    initial_coros: list[Callable],
    controller_api: ControllerAPI,
):
    for attribute in controller_api.attributes.values():
        match attribute:
            case (
                AttrR(_io_ref=AttributeIORef(update_period=update_period)) as attribute
            ):
                if update_period is ONCE:
                    initial_coros.append(attribute.bind_update_callback())
                elif update_period is not None:
                    scan_dict[update_period].append(attribute.bind_update_callback())


def _get_periodic_scan_coros(
    scan_dict: dict[float, list[Scan]],
) -> list[ScanCallback]:
    periodic_scan_coros: list[ScanCallback] = []
    for period, methods in scan_dict.items():
        periodic_scan_coros.append(_create_periodic_scan_coro(period, methods))

    return periodic_scan_coros


def _create_periodic_scan_coro(period: float, scans: list[Scan]) -> ScanCallback:
    async def _sleep():
        await asyncio.sleep(period)

    methods = [_sleep] + scans  # Create periodic behavior

    async def scan_coro() -> None:
        while True:
            await asyncio.gather(*[method() for method in methods])

    return scan_coro
