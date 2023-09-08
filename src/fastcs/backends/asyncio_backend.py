from softioc import asyncio_dispatcher, softioc

from fastcs.backend import Backend
from fastcs.mapping import Mapping


class AsyncioBackend:
    def __init__(self, mapping: Mapping):
        self._mapping = mapping

    def run_interactive_session(self):
        # Create an asyncio dispatcher; the event loop is now running
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()

        backend = Backend(self._mapping, dispatcher.loop)

        backend.link_process_tasks()
        backend.run_initial_tasks()
        backend.start_scan_tasks()

        # Run the interactive shell
        global_variables = globals()
        global_variables.update(
            {
                "dispatcher": dispatcher,
                "mapping": self._mapping,
                "controller": self._mapping.controller,
            }
        )
        softioc.interactive_ioc(globals())
