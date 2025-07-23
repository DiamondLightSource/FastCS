from asyncio import iscoroutinefunction
from collections.abc import Callable, Coroutine
from inspect import Signature, getdoc, signature
from types import MethodType
from typing import Any, Generic, TypeVar

from fastcs.controller import BaseController

from .exceptions import FastCSException

MethodCallback = Callable[..., Coroutine[None, None, None]]
"""Generic base class for all `Controller` methods"""
Controller_T = TypeVar("Controller_T", bound=BaseController)
"""Generic `Controller` class that an unbound method must be called with as `self`"""
UnboundCommandCallback = Callable[[Controller_T], Coroutine[None, None, None]]
"""A Command callback that is unbound and must be called with a `Controller` instance"""
UnboundScanCallback = Callable[[Controller_T], Coroutine[None, None, None]]
"""A Scan callback that is unbound and must be called with a `Controller` instance"""
UnboundPutCallback = Callable[[Controller_T, Any], Coroutine[None, None, None]]
"""A Put callback that is unbound and must be called with a `Controller` instance"""
CommandCallback = Callable[[], Coroutine[None, None, None]]
"""A Command callback that is bound and can be called without `self`"""
ScanCallback = Callable[[], Coroutine[None, None, None]]
"""A Scan callback that is bound and can be called withous `self`"""
PutCallback = Callable[[Any], Coroutine[None, None, None]]
"""A Put callback that is bound and can be called without `self`"""


method_not_bound_error = NotImplementedError(
    "Method must be bound to a controller instance to be callable"
)


class Method(Generic[Controller_T]):
    """Generic base class for all FastCS Controller methods."""

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


class Command(Method[BaseController]):
    """A `Controller` `Method` that performs a single action when called.

    This class contains a function that is bound to a specific `Controller` instance and
    is callable outside of the class context, without an explicit `self` parameter.
    Calling an instance of this class will call the bound `Controller` method.
    """

    def __init__(self, fn: CommandCallback, *, group: str | None = None):
        super().__init__(fn, group=group)

    def _validate(self, fn: CommandCallback) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 0:
            raise FastCSException(f"Command method cannot have arguments: {fn}")

    async def __call__(self):
        return await self._fn()


class Scan(Method[BaseController]):
    """A `Controller` `Method` that will be called periodically in the background.

    This class contains a function that is bound to a specific `Controller` instance and
    is callable outside of the class context, without an explicit `self` parameter.
    Calling an instance of this class will call the bound `Controller` method.
    """

    def __init__(self, fn: ScanCallback, period: float):
        super().__init__(fn)

        self._period = period

    @property
    def period(self):
        return self._period

    def _validate(self, fn: ScanCallback) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 0:
            raise FastCSException("Scan method cannot have arguments")

    async def __call__(self):
        return await self._fn()


class Put(Method[BaseController]):
    """Why don't know what this is for."""

    def __init__(self, fn: PutCallback):
        super().__init__(fn)

    def _validate(self, fn: PutCallback) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Put method can only take one argument")

    async def __call__(self, value: Any):
        return await self._fn(value)


class UnboundCommand(Method[Controller_T]):
    """A wrapper of an unbound `Controller` method to be bound into a `Command`.

    This generic class stores an unbound `Controller` method - effectively a function
    that takes an instance of a specific `Controller` type (`Controller_T`). Instances
    of this class can be added at `Controller` definition, either manually or with use
    of the `command` wrapper, to register the method to be included in the API of the
    `Controller`. When the `Controller` is instantiated, these instances will be bound
    to the instance, creating a `Command` instance.
    """

    def __init__(
        self, fn: UnboundCommandCallback[Controller_T], *, group: str | None = None
    ) -> None:
        super().__init__(fn, group=group)

    def _validate(self, fn: UnboundCommandCallback[Controller_T]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Command method cannot have arguments")

    def bind(self, controller: Controller_T) -> Command:
        return Command(MethodType(self.fn, controller), group=self.group)

    def __call__(self):
        raise method_not_bound_error


class UnboundScan(Method[Controller_T]):
    """A wrapper of an unbound `Controller` method to be bound into a `Scan`.

    This generic class stores an unbound `Controller` method - effectively a function
    that takes an instance of a specific `Controller` type (`Controller_T`). Instances
    of this class can be added at `Controller` definition, either manually or with use
    of the `scan` wrapper, to register the method to be included in the API of the
    `Controller`. When the `Controller` is instantiated, these instances will be bound
    to the instance, creating a `Scan` instance.
    """

    def __init__(self, fn: UnboundScanCallback[Controller_T], period: float) -> None:
        super().__init__(fn)

        self._period = period

    @property
    def period(self):
        return self._period

    def _validate(self, fn: UnboundScanCallback[Controller_T]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 1:
            raise FastCSException("Scan method cannot have arguments")

    def bind(self, controller: Controller_T) -> Scan:
        return Scan(MethodType(self.fn, controller), self._period)

    def __call__(self):
        raise method_not_bound_error


class UnboundPut(Method[Controller_T]):
    """Unbound version of `Put`."""

    def __init__(self, fn: UnboundPutCallback[Controller_T]) -> None:
        super().__init__(fn)

    def _validate(self, fn: UnboundPutCallback[Controller_T]) -> None:
        super()._validate(fn)

        if not len(self.parameters) == 2:
            raise FastCSException("Put method can only take one argument")

    def bind(self, controller: Controller_T) -> Put:
        return Put(MethodType(self.fn, controller))

    def __call__(self):
        raise method_not_bound_error
