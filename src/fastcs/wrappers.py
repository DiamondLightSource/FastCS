from typing import Any

from .cs_methods import MethodInfo, MethodType
from .exceptions import FastCSException


# TODO: Consider type hints with the use of typing.Protocol
def scan(period: float) -> Any:
    if period <= 0:
        raise FastCSException("Scan method must have a positive scan period")

    def wrapper(fn):
        fn.fastcs_method_info = MethodInfo(MethodType.scan, fn, period=period)
        return fn

    return wrapper


def put(fn) -> Any:
    fn.fastcs_method_info = MethodInfo(MethodType.put, fn)
    return fn


def command(fn) -> Any:
    fn.fastcs_method_info = MethodInfo(MethodType.command, fn)
    return fn
