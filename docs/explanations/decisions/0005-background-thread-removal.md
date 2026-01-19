# 5. Remove Background Thread from Backend

Date: 2025-01-24

**Related:** [PR #98](https://github.com/DiamondLightSource/FastCS/pull/98)

## Status

Accepted

## Context

The original FastCS Backend implementation used `asyncio.run_coroutine_threadsafe()` to execute controller operations on a background event loop thread managed by `AsyncioDispatcher`. This pattern was inherited from EPICS softIOC's threading model.

**Original Architecture - Background Thread:**

```python
class Backend:
    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        # Create dispatcher with its own thread
        self.dispatcher = AsyncioDispatcher(loop)
        self._loop = self.dispatcher.loop  # Runs in background thread

        # Run initialization on background thread
        asyncio.run_coroutine_threadsafe(
            self._controller.initialise(), self._loop
        ).result()  # Block until complete

    def _run_initial_futures(self):
        for coro in self._initial_coros:
            # Schedule on background thread, block main thread
            future = asyncio.run_coroutine_threadsafe(coro(), self._loop)
            future.result()

    def start_scan_futures(self):
        # Store Future objects from background thread
        self._scan_futures = {
            asyncio.run_coroutine_threadsafe(coro(), self._loop)
            for coro in _get_scan_coros(self._controller)
        }
```

This approach created a threading model where:
- Main thread creates Backend
- AsyncioDispatcher starts background thread with event loop
- Controller operations scheduled from main thread to background thread
- Main thread blocks waiting for background thread results via `.result()`

**Problems with Background Thread:**

1. **Thread Safety Complexity:** Managing state across thread boundaries introduced race conditions and required careful synchronization:
   - Controller state accessed from both threads
   - Attribute updates needed thread-safe mechanisms
   - Future cancellation had timing issues

2. **Blocking Main Thread:** Despite using async, the main thread blocked waiting for background thread operations:
   ```python
   future = asyncio.run_coroutine_threadsafe(coro(), self._loop)
   future.result()  # Main thread blocks here
   ```
   This defeated the purpose of async programming

3. **Complex Lifecycle Management:** Starting and stopping the background thread added complexity:
   - Ensuring thread cleanup in `__del__`
   - Managing Future objects for scan tasks
   - Cancelling futures vs cancelling tasks had different semantics

4. **Difficult to Test:** Background threads made tests:
   - Non-deterministic (race conditions)
   - Harder to debug (multiple call stacks)
   - Slower (thread startup overhead)

5. **Unnecessary for Most Transports:** Only EPICS CA softIOC actually required a background thread (due to its C library's threading requirements). Other transports (REST, GraphQL, Tango, PVA) could run entirely async:
   - REST/GraphQL use async frameworks (FastAPI, Strawberry)
   - EPICS PVA is pure Python async

6. **Future vs Task Confusion:** Using `Future` objects from `run_coroutine_threadsafe()` instead of `Task` objects from `create_task()` created API inconsistencies

The system needed a simpler concurrency model that:
- Runs all async code on a single event loop
- Uses native async/await throughout
- Eliminates thread synchronization complexity
- Allows transports to manage their own threading if needed

## Decision

We removed the background thread from Backend, making it fully async and allowing transports to manage their own threading requirements if needed.

### New Architecture

**Async-Only Backend:**

```python
class Backend:
    def __init__(
        self,
        controller: Controller,
        loop: asyncio.AbstractEventLoop,  # Now required, not created
    ):
        self._loop = loop  # Caller's event loop
        self._controller = controller

        self._initial_coros = [controller.connect]
        self._scan_tasks: set[asyncio.Task] = set()  # Tasks, not Futures

        # Run initialization on PROVIDED event loop (not background thread)
        loop.run_until_complete(self._controller.initialise())
        self._link_process_tasks()

    async def serve(self):
        """Fully async - no blocking"""
        await self._run_initial_coros()
        await self._start_scan_tasks()

    async def _run_initial_coros(self):
        """Direct await - no threading"""
        for coro in self._initial_coros:
            await coro()

    async def _start_scan_tasks(self):
        """Create tasks on same event loop"""
        self._scan_tasks = {
            self._loop.create_task(coro())
            for coro in _get_scan_coros(self._controller)
        }
```

### Key Changes

1. **No AsyncioDispatcher:**
   - Removed `self.dispatcher = AsyncioDispatcher(loop)`
   - Backend now receives event loop from caller
   - No background thread creation

2. **Synchronous Initialization:**
   - **Before:** `asyncio.run_coroutine_threadsafe().result()` (cross-thread blocking)
   - **After:** `loop.run_until_complete()` (same-thread blocking)
   - Initialization happens before event loop starts running

3. **Async serve() Method:**
   - **Before:** `run()` method that scheduled futures
   - **After:** `async serve()` method using native async/await
   - Can be composed with other async operations

4. **Tasks Instead of Futures:**
   - **Before:** `asyncio.run_coroutine_threadsafe()` returns `Future`
   - **After:** `loop.create_task()` returns `Task`
   - Consistent with async best practices

5. **Transport-Managed Threading:**
   - EPICS CA transport creates its own AsyncioDispatcher when needed
   - Other transports run purely async
   - Each transport decides its threading model

### Benefits

- **Simplified Concurrency Model:** Single event loop for most operations, no cross-thread coordination

- **True Async/Await:** Native Python async patterns throughout, no blocking `.result()` calls

- **Better Testability:** Deterministic execution, easier to debug, faster tests

- **Clearer Responsibility:** Transports that need threads manage them explicitly

- **Task-Based API:** Consistent use of `Task` objects with cancellation support

- **Composability:** `async serve()` can be composed with other async operations

- **Performance:** Eliminated thread creation overhead for transports that don't need it

## Consequences

The Tango transport still requires being run on in a background thread because it does
not allow an event loop to be passed it. It always creates its own and then the issues
with coroutines being called from the wrong event loop persist.

### Technical Changes

- 769 insertions, 194 deletions across 27 files
- Removed `AsyncioDispatcher` from `src/fastcs/backend.py`
- Changed `Backend.__init__()` to accept event loop (not create it)
- Changed `Backend.run()` to `async Backend.serve()`
- Updated initialization from `run_coroutine_threadsafe()` to `run_until_complete()`
- Changed scan task management from `Future` to `Task` objects
- Updated all transport adapters:
  - `src/fastcs/transport/epics/adapter.py` - Now creates dispatcher
  - `src/fastcs/transport/graphql/adapter.py` - Pure async
  - `src/fastcs/transport/rest/adapter.py` - Pure async
  - `src/fastcs/transport/tango/adapter.py` - Updated async handling
- Added benchmarking tests in `tests/benchmarking/`
- Updated `src/fastcs/launch.py` to handle async serve

### Migration Impact

For transport developers:

**Before (Background thread in Backend):**
```python
class MyTransport(TransportAdapter):
    def __init__(self, controller_api, loop):
        # Backend created its own thread
        self._backend = Backend(controller)

    def run(self):
        self._backend.run()  # Synchronous
        # Do transport-specific work
```

**After (Async serve):**
```python
class MyTransport(Transport):
    def connect(self, controller_api, loop):
        # Pass loop to Backend
        self._backend = Backend(controller, loop)

    async def serve(self):
        await self._backend.serve()  # Async
        # Do transport-specific work
```

For transports needing threads (like EPICS CA):

```python
class EpicsCATransport(Transport):
    def __init__(self):
        # Transport creates its own dispatcher
        self._dispatcher = AsyncioDispatcher()

    def connect(self, controller_api, loop):
        # Use dispatcher's loop for Backend
        self._backend = Backend(controller, self._dispatcher.loop)

    async def serve(self):
        # Bridge to threaded environment
        await self._backend.serve()
```

### Performance Impact

Benchmarking showed:
- Faster startup (no thread creation for most transports)
- Reduced memory overhead (no extra thread stack)
- More predictable timing (no thread scheduling delays)
- Better CPU utilization (single event loop)

### Architectural Impact

The removal of the background thread simplified FastCS's concurrency model, making it more predictable, testable, and performant while still supporting transports that require threading (like EPICS CA) through explicit transport-level thread management.
