import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic

from fastcs.datatypes import DType_T

AttrValuePredicate = Callable[[DType_T], bool]


@dataclass(eq=False)
class PredicateEvent(Generic[DType_T]):
    """A wrapper of `asyncio.Event` that only triggers when a predicate is satisfied"""

    _predicate: AttrValuePredicate[DType_T]
    """Predicate to filter set calls by"""
    _event: asyncio.Event = field(default_factory=asyncio.Event)
    """Event to set"""

    def set(self, value: DType_T) -> bool:
        """Set the event if the predicate is satisfied by the value

        Returns:
            `True` if the predicate was satisfied and the event was set, else `False`

        """
        if self._predicate(value):
            self._event.set()
            return True

        return False

    async def wait(self):
        """Wait for the event to be set"""
        await self._event.wait()

    def __hash__(self) -> int:
        """Make instances unique when stored in sets"""
        return id(self)
