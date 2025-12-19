from asyncio import iscoroutinefunction
from collections.abc import Callable, Coroutine
from inspect import Signature, getdoc, signature
from typing import TYPE_CHECKING, Generic, TypeVar

from fastcs.tracer import Tracer

if TYPE_CHECKING:
    from fastcs.controllers import BaseController  # noqa: F401

MethodCallback = Callable[..., Coroutine[None, None, None]]
"""Generic protocol for all `Controller` Method callbacks"""
Controller_T = TypeVar("Controller_T", bound="BaseController")  # noqa: F821
"""Generic `Controller` class that an unbound method must be called with as `self`"""


class Method(Generic[Controller_T], Tracer):
    """Generic base class for all FastCS Controller methods."""

    def __init__(self, fn: MethodCallback, *, group: str | None = None) -> None:
        super().__init__()

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
            raise TypeError("Method return type must be None or empty")

        if not iscoroutinefunction(fn):
            raise TypeError("Method must be async function")

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
