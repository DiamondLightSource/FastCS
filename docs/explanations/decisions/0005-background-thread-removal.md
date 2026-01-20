# 5. Remove Background Thread from Backend

Date: 2025-01-24

**Related:** [PR #98](https://github.com/DiamondLightSource/FastCS/pull/98)

## Status

Accepted

## Context

The current FastCS Backend implementation uses `asyncio.run_coroutine_threadsafe()` to execute controller operations on a background event loop thread managed by `AsyncioDispatcher`. This threading model creates several problems:

- **Thread Safety Complexity:** Managing state across thread boundaries introduced race conditions and required careful synchronization
- **Blocked Main Thread:** Despite using async, the main thread blocked waiting for background thread results via `.result()`
- **Complex Lifecycle Management:** Starting and stopping the background thread added complexity
- **Difficult to Test:** Background threads made tests non-deterministic and harder to debug
- **Unnecessary for Most Transports:** Only EPICS CA softIOC actually needed a background thread; other transports (REST, GraphQL, PVA) could run entirely async

The system needs a simpler concurrency model that uses native async/await patterns and allows transports to manage their own threading if needed.

## Decision

Remove the background thread from Backend, making it fully async, while allowing specific transports to use a background thread if required. Tango does require this because it does not accept an event loop to run on. Backend now accepts an event loop from the caller and uses native async/await throughout. Transports that need threading (like EPICS CA) manage their own threading explicitly.

Key architectural changes:
- Backend receives event loop from caller (no background dispatcher)
- Initialization uses `loop.run_until_complete()` instead of cross-thread scheduling
- Backend exposes `async serve()` method using native async/await patterns
- Scan tasks use `Task` objects from `loop.create_task()` instead of `Future` objects
- Transports that need threading create their own `AsyncioDispatcher` when needed

## Consequences

### Benefits

- **Simpler Concurrency Model:** Single event loop for most operations, no cross-thread coordination needed
- **True Async/Await:** Native Python async patterns throughout, no blocking `.result()` calls
- **Better Testability:** Deterministic execution, easier to debug, no thread scheduling delays
- **Clearer Responsibility:** Transports explicitly manage threading they need
- **Task-Based API:** Consistent use of `Task` objects with standard cancellation support
- **Composability:** `async serve()` can be composed with other async operations

### Migration Pattern

**Before (Background thread in Backend):**
```python
class MyTransport(TransportAdapter):
    def __init__(self, controller_api, loop):
        self._backend = Backend(controller)  # Creates background thread

    def run(self):
        self._backend.run()  # Synchronous

# Client code
asyncio.run_coroutine_threadsafe(coro(), self._loop)  # Cross-thread scheduling
future.result()  # Main thread blocks
```

**After (Async-only Backend):**
```python
class MyTransport(Transport):
    def connect(self, controller_api, loop):
        self._backend = Backend(controller, loop)  # Use caller's loop

    async def serve(self):
        await self._backend.serve()  # Native async

# Client code
await self._backend.serve()  # Direct await, no threading
```

**For transports needing threads (EPICS CA):**
```python
class EpicsCATransport(Transport):
    def __init__(self):
        self._dispatcher = AsyncioDispatcher()  # Transport manages its own thread

    def connect(self, controller_api, loop):
        self._backend = Backend(controller, self._dispatcher.loop)

    async def serve(self):
        await self._backend.serve()  # Bridge to threaded environment
```
