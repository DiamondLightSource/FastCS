from asyncio import iscoroutinefunction
from collections.abc import Callable, Coroutine
from inspect import Signature, getdoc, signature
from types import MethodType
from typing import Any, Concatenate, Generic, ParamSpec, TypeVar

from fastcs.controller import BaseController

from .exceptions import FastCSException

ControllerType = TypeVar("ControllerType", bound=BaseController)
# These callbacks are `Controller` instance methods, so the first parameter is `self`
MethodCallback = Callable[..., Coroutine[None, None, Any]]
CommandCallback = Callable[[ControllerType], Coroutine[None, None, None]]
ScanCallback = Callable[[ControllerType], Coroutine[None, None, None]]
PutCallback = Callable[[ControllerType, Any], Coroutine[None, None, None]]
BoundCommandCallback = Callable[[], Coroutine[None, None, None]]
BoundScanCallback = Callable[[], Coroutine[None, None, None]]
BoundPutCallback = Callable[[Any], Coroutine[None, None, None]]


method_not_bound_error = NotImplementedError(
    "Method must be bound to a controller instance to be callable"
)


class Method(Generic[ControllerType]):
    def __init__(self, fn: MethodCallback, *, group: str | None = None) -> None:
        self._docstring = getdoc(fn)

        sig = signature(fn, eval_str=True)
        self._parameters = sig.parameters
        self._return_type = sig.return_annotation
        self._validate(fn)

        self._fn = fn
        self._group = group
        self.enabled = True

    def _validate(self, fn: MethodCallback) -> None:
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


class Scan(Method[ControllerType]):
    def __init__(self, fn: ScanCallback[ControllerType], period: float) -> None:
        super().__init__(fn)

        self._period = period

    @property
    def period(self):
        return self._period

    def _validate(self, fn: ScanCallback[ControllerType]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Scan method cannot have arguments")

    def bind(self, controller: ControllerType) -> "BoundScan":
        return BoundScan(MethodType(self.fn, controller), self._period)

    def __call__(self):
        raise method_not_bound_error


class Put(Method[ControllerType]):
    def __init__(self, fn: PutCallback[ControllerType]) -> None:
        super().__init__(fn)

    def _validate(self, fn: PutCallback[ControllerType]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 2:
            raise FastCSException("Put method can only take one argument")

    def bind(self, controller: ControllerType) -> "BoundPut":
        return BoundPut(MethodType(self.fn, controller))

    def __call__(self, value: Any):
        raise method_not_bound_error


class Command(Method[ControllerType]):
    def __init__(
        self, fn: CommandCallback[ControllerType], *, group: str | None = None
    ) -> None:
        super().__init__(fn, group=group)

    def _validate(self, fn: CommandCallback[ControllerType]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Command method cannot have arguments")

    def bind(self, controller: ControllerType) -> "BoundCommand":
        return BoundCommand(MethodType(self.fn, controller))

    def __call__(self):
        raise method_not_bound_error


P = ParamSpec("P")
R = TypeVar("R")


class BoundScan(Method[BaseController], Generic[P]):
    def __init__(self, fn: Callable[Concatenate[ControllerType, P], R], period: float):
        self._fn = fn
        self._period = period

    @property
    def period(self):
        return self._period

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self._fn(*args, **kwargs)


class BoundPut(Method[BaseController]):
    def __init__(self, fn: BoundPutCallback):
        super().__init__(fn)

    def _validate(self, fn: BoundPutCallback) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Put method can only take one argument")

    def __call__(self, value: Any):
        return self._fn(value)


class BoundCommand(Method[BaseController]):
    def __init__(self, fn: BoundCommandCallback):
        super().__init__(fn)

    def _validate(self, fn: BoundCommandCallback) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 0:
            raise FastCSException("Command method cannot have arguments")

    def __call__(self):
        return self._fn()
