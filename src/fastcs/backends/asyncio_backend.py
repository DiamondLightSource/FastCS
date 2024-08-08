from softioc import softioc

from fastcs.backend import Backend
from fastcs.controller import Controller


class AsyncioBackend(Backend):
    def __init__(self, controller: Controller):  # noqa: F821
        super().__init__(controller)

    def _run(self):
        # Run the interactive shell
        softioc.interactive_ioc(self._context)
