import asyncio

from fastcs.backend import Backend


def test_backend(controller):
    loop = asyncio.get_event_loop()
    backend = Backend(controller, loop)

    # Controller should be initialised by Backend and not connected
    assert controller.initialised
    assert not controller.connected

    # Controller Attributes with a Sender should have a _process_callback created
    assert controller.read_write_int.has_process_callback()

    async def test_wrapper():
        loop.create_task(backend.serve())
        await asyncio.sleep(0)  # Yield to task

        # Controller should have been connected by Backend
        assert controller.connected

        # Scan tasks should be running
        for _ in range(3):
            count = controller.count
            await asyncio.sleep(0.01)
            assert controller.count > count
        backend._stop_scan_tasks()

    loop.run_until_complete(test_wrapper())
