from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from inspect import Signature, getdoc, signature

from .exceptions import FastCSException

ScanCallback = Callable[..., Awaitable[None]]


class Method:
    def __init__(self, fn: Callable, *, group: str | None = None) -> None:
        self._docstring = getdoc(fn)

        sig = signature(fn, eval_str=True)
        self._parameters = sig.parameters
        self._return_type = sig.return_annotation
        self._validate(fn)

        self._fn = fn
        self._group = group

    def _validate(self, fn: Callable) -> None:
        if self.return_type not in (None, Signature.empty):
            raise FastCSException("Method return type must be None or empty")

        if not iscoroutinefunction(fn):
            raise FastCSException("Method must be async function")

    @property
    def return_type(self):
        return self._return_type

    @property
    def parameters(self):
        return self._parameters

    @property
    def docstring(self):
        return self._docstring

    @property
    def fn(self):
        return self._fn

    @property
    def group(self):
        return self._group


class Scan(Method):
    def __init__(self, fn: Callable, period) -> None:
        super().__init__(fn)

        self._period = period

    def _validate(self, fn: Callable) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Scan method cannot have arguments")

    @property
    def period(self):
        return self._period


class Put(Method):
    def __init__(self, fn: Callable) -> None:
        super().__init__(fn)

    def _validate(self, fn: Callable) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 2:
            raise FastCSException("Put method can only take one argument")


class Command(Method):
    def __init__(self, fn: Callable, *, group: str | None = None) -> None:
        super().__init__(fn, group=group)

    def _validate(self, fn: Callable) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Command method cannot have arguments")
