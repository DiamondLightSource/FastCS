from collections.abc import Callable

from .cs_methods import (
    Command,
    CommandCallback,
    ControllerType,
    Put,
    PutCallback,
    Scan,
    ScanCallback,
)


def scan(
    period: float,
) -> Callable[[ScanCallback[ControllerType]], Scan[ControllerType]]:
    if period <= 0:
        raise ValueError("Scan method must have a positive scan period")

    def wrapper(fn: ScanCallback[ControllerType]) -> Scan[ControllerType]:
        return Scan(fn, period)

    return wrapper


def put(fn: PutCallback[ControllerType]) -> Put[ControllerType]:
    return Put(fn)


def command(
    *, group: str | None = None
) -> Callable[[CommandCallback[ControllerType]], Command[ControllerType]]:
    def wrapper(fn: CommandCallback[ControllerType]) -> Command[ControllerType]:
        return Command(fn, group=group)

    return wrapper
