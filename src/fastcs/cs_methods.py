from asyncio import iscoroutinefunction
from collections.abc import Callable, Coroutine
from inspect import Signature, getdoc, signature
from typing import Any, Generic, TypeVar

from fastcs.controller import BaseController

from .exceptions import FastCSException

ControllerType = TypeVar("ControllerType", bound=BaseController)
# These callbacks are `Controller` instance methods, so the first parameter is `self`
MethodCallback = Callable[..., Coroutine[None, None, Any]]
CommandCallback = Callable[[ControllerType], Coroutine[None, None, None]]
ScanCallback = Callable[[ControllerType], Coroutine[None, None, None]]
PutCallback = Callable[[ControllerType, Any], Coroutine[None, None, None]]


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

    def _validate(self, fn: ScanCallback[ControllerType]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Scan method cannot have arguments")

    @property
    def period(self):
        return self._period


class Put(Method[ControllerType]):
    def __init__(self, fn: PutCallback[ControllerType]) -> None:
        super().__init__(fn)

    def _validate(self, fn: PutCallback[ControllerType]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 2:
            raise FastCSException("Put method can only take one argument")


class Command(Method[ControllerType]):
    def __init__(
        self, fn: CommandCallback[ControllerType], *, group: str | None = None
    ) -> None:
        super().__init__(fn, group=group)

    def _validate(self, fn: CommandCallback[ControllerType]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Command method cannot have arguments")


class BoundScan(Scan):
    def __init__(self, scan: Scan[BaseController], controller: BaseController) -> None:
        super().__init__(scan.fn, scan.period)

        self._controller = controller

    async def __call__(self):
        return await self._fn(self._controller)


class BoundPut(Put):
    def __init__(self, put: Put, controller: BaseController) -> None:
        super().__init__(put.fn)

        self._controller = controller

    async def __call__(self, value: bool | int | float | str):
        return await self._fn(self._controller, value)


class BoundCommand(Command):
    def __init__(self, command: Command, controller: BaseController) -> None:
        super().__init__(command.fn)

        self._controller = controller

    async def __call__(self):
        return await self._fn(self._controller)
