from typing import Any, Protocol

from .cs_methods import Command, Method, Put, Scan
from .exceptions import FastCSException


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


def command(fn) -> Any:
    fn.fastcs_method = Command(fn)
    return fn
