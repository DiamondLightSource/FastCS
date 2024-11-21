import asyncio

import pytest

from fastcs.backend import Backend


class DummyBackend(Backend):
    def __init__(self, controller):
        super().__init__(controller)

        self.init_task_called = False
        self._initial_coros.append(self.init_task)

    async def init_task(self):
        self.init_task_called = True

    def _run(self):
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0.3), self._loop)


@pytest.mark.asyncio
async def test_backend(controller):
    backend = DummyBackend(controller)

    # Controller should be initialised by Backend, but not connected
    assert controller.initialised
    assert not controller.connected

    # Controller Attributes with a Sender should have a _process_callback created
    assert controller.read_write_int.has_process_callback()

    backend.run()

    # Controller should have been connected by Backend
    assert controller.connected

    # Initial tasks should be complete
    assert backend.init_task_called

    # Scan tasks should be running
    for _ in range(3):
        count = controller.count
        await asyncio.sleep(0.1)
        assert controller.count > count

    backend.stop_scan_futures()
