from typing import Any, Protocol, runtime_checkable

from .cs_methods import Command, Method, Put, Scan
from .exceptions import FastCSException


@runtime_checkable
class WrappedMethod(Protocol):
    fastcs_method: Method


# TODO: Consider type hints with the use of typing.Protocol
def scan(period: float) -> Any:
    if period <= 0:
        raise FastCSException("Scan method must have a positive scan period")

    def wrapper(fn):
        fn.fastcs_method = Scan(fn, period)
        return fn

    return wrapper


def put(fn) -> Any:
    fn.fastcs_method = Put(fn)
    return fn


def command(*, group: str | None = None) -> Any:
    """Decorator to map a `Controller` method into a `Command`.

    Args:
        group: Group to display the widget for this command in on the UI

    """

    def wrapper(fn):
        fn.fastcs_method = Command(fn, group=group)
        return fn

    return wrapper
