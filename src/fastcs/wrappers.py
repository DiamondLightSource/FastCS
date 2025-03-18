from collections.abc import Callable

from .cs_methods import (
    Controller_T,
    UnboundCommand,
    UnboundCommandCallback,
    UnboundPut,
    UnboundPutCallback,
    UnboundScan,
    UnboundScanCallback,
)
from .exceptions import FastCSException


def scan(
    period: float,
) -> Callable[[UnboundScanCallback[Controller_T]], UnboundScan[Controller_T]]:
    """Sets up a scan over the wrapped method."""

    if period <= 0:
        raise FastCSException("Scan method must have a positive scan period")

    def wrapper(fn: UnboundScanCallback[Controller_T]) -> UnboundScan[Controller_T]:
        return UnboundScan(fn, period)

    return wrapper


def put(fn: UnboundPutCallback[Controller_T]) -> UnboundPut[Controller_T]:
    """Sets up a put over the wrapped method."""
    return UnboundPut(fn)


def command(
    *, group: str | None = None
) -> Callable[[UnboundCommandCallback[Controller_T]], UnboundCommand[Controller_T]]:
    """Decorator to tag a `Controller` method to be turned into a `Command`.

    Args:
        group: Group to display this command under in the transport layer

    """

    def wrapper(
        fn: UnboundCommandCallback[Controller_T],
    ) -> UnboundCommand[Controller_T]:
        return UnboundCommand(fn, group=group)

    return wrapper
