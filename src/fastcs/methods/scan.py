from collections.abc import Callable, Coroutine
from types import MethodType

from fastcs.controllers import BaseController
from fastcs.methods.method import Controller_T, Method

UnboundScanCallback = Callable[[Controller_T], Coroutine[None, None, None]]
"""A Scan callback that is unbound and must be called with a `Controller` instance"""
ScanCallback = Callable[[], Coroutine[None, None, None]]
"""A Scan callback that is bound and can be called without `self`"""


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
            raise TypeError("Scan method cannot have arguments")

    async def __call__(self):
        return await self._fn()


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
            raise TypeError("Scan method cannot have arguments")

    def bind(self, controller: Controller_T) -> Scan:
        return Scan(MethodType(self.fn, controller), self._period)

    def __call__(self):
        raise NotImplementedError(
            "Method must be bound to a controller instance to be callable"
        )


def scan(
    period: float,
) -> Callable[[UnboundScanCallback[Controller_T]], UnboundScan[Controller_T]]:
    """Decorator to register a `Controller` method as a `Scan`

    The `Scan` method will be called periodically in the background.
    """

    if period <= 0:
        raise ValueError("Scan method must have a positive scan period")

    def wrapper(fn: UnboundScanCallback[Controller_T]) -> UnboundScan[Controller_T]:
        return UnboundScan(fn, period)

    return wrapper
