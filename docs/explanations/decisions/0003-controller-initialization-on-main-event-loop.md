# 3. Controller Initialization on Main Event Loop

Date: 2024-08-01

**Related:** [PR #49](https://github.com/DiamondLightSource/FastCS/pull/49)

## Status

Accepted

## Context

In the original FastCS architecture, the Backend class initialization pattern made it difficult for controllers to perform async setup operations on the main event loop before their API was exposed through the Mapping layer.

**Original Architecture - Separate Initialization:**

The AsyncioBackend used composition, creating separate components and manually orchestrating initialization:

```python
class AsyncioBackend:
    def __init__(self, mapping: Mapping):
        self._mapping = mapping

    def run_interactive_session(self):
        dispatcher = AsyncioDispatcher()
        backend = Backend(self._mapping, dispatcher.loop)

        # Manual initialization sequence
        backend.link_process_tasks()
        backend.run_initial_tasks()
        backend.start_scan_tasks()
```

The Backend was a thin wrapper that accepted a pre-created Mapping:

```python
class Backend:
    def __init__(self, mapping: Mapping, loop: asyncio.AbstractEventLoop):
        self._mapping = mapping
        self._loop = loop
```

The system needed a way to:
- Allow controllers to run async initialization code on the main event loop
- Ensure initialization happens before the Mapping is created
- Provide a consistent Backend base class with a clear lifecycle
- Centralize initialization orchestration in one place

## Decision

We redesigned the Backend class to own the entire initialization lifecycle, including creating the event loop and running controller initialization on it before creating the Mapping.

### New Architecture

**Backend - Lifecycle Orchestrator:**

```python
class Backend:
    def __init__(
        self, controller: Controller, loop: asyncio.AbstractEventLoop | None = None
    ):
        # 1. Create AsyncioDispatcher with optional loop
        self._dispatcher = AsyncioDispatcher(loop)
        self._loop = self._dispatcher.loop
        self._controller = controller

        # 2. Add connect to initial tasks
        self._initial_tasks.append(controller.connect)

        # 3. KEY CHANGE: Run controller.initialise() on main event loop
        #    BEFORE creating the Mapping
        asyncio.run_coroutine_threadsafe(
            self._controller.initialise(), self._loop
        ).result()

        # 4. Create Mapping AFTER controller is initialized
        self._mapping = Mapping(self._controller)
        self._link_process_tasks()

        # 5. Build context dictionary for subclasses
        self._context.update({
            "dispatcher": self._dispatcher,
            "controller": self._controller,
            "mapping": self._mapping,
        })

    def run(self):
        self._run_initial_tasks()
        self._start_scan_tasks()
        self._run()  # Subclass-specific implementation
```

### Key Changes

1. **Controller Initialization on Main Event Loop:**
   - Added `initialise()` method to Controller class as an async initialization hook
   - Backend calls `asyncio.run_coroutine_threadsafe(controller.initialise(), self._loop).result()`
   - This happens BEFORE the Mapping is created, allowing controllers to set up async resources

2. **Backend Accepts Controller, Not Mapping:**
   - **Before:** `Backend(mapping: Mapping, loop: AbstractEventLoop)`
   - **After:** `Backend(controller: Controller, loop: AbstractEventLoop | None = None)`
   - Backend now owns creating the Mapping after initialization

3. **Inheritance-Based Architecture:**
   - **Before:** AsyncioBackend used composition, creating Backend separately
   - **After:** All backends inherit from Backend base class
   - Subclasses implement `_run()` for protocol-specific execution

4. **Centralized Lifecycle:**
   - Backend orchestrates: `initialise()` → create Mapping → `connect()` → scan tasks → `_run()`
   - Clear, documented initialization sequence
   - Consistent across all backend types

5. **Unified Context Management:**
   - Backend maintains `_context` dictionary with dispatcher, controller, and mapping
   - Passed to subclass `_run()` implementations
   - Consistent context across all backends

### Controller Lifecycle

```python
class Controller(BaseController):
    async def initialise(self) -> None:
        """Called on main event loop BEFORE Mapping creation.
        Override to perform async setup (database connections, etc.)"""
        pass

    async def connect(self) -> None:
        """Called as initial task AFTER Mapping creation.
        Override to establish device connections."""
        pass
```

### Benefits

- **Async Initialization Support:** Controllers can now perform async setup on the main
  event loop before their API is exposed. This allows introspecting devices to create
  Attributes and Methods dynamically.

- **Predictable Lifecycle:** Clear initialization sequence: initialise → Mapping → connect → scan

- **Better Separation of Concerns:**
  - Backend: Infrastructure and lifecycle management
  - Subclasses: Protocol-specific `_run()` implementation
  - Controller: Domain logic and initialization

- **Cleaner API:** Backends accept Controller directly, not pre-created Mapping

## Consequences

### Technical Changes

- 358 insertions, 217 deletions across 13 files
- Restructured `src/fastcs/backend.py` with new lifecycle orchestration
- Added `initialise()` method to `src/fastcs/controller.py`
- Updated all backend implementations to inherit from Backend:
  - `src/fastcs/backends/asyncio_backend.py`
  - `src/fastcs/backends/epics/backend.py`
  - `src/fastcs/backends/tango/backend.py`
- Updated corresponding IOC/runtime implementations:
  - `src/fastcs/backends/epics/ioc.py`
  - `src/fastcs/backends/tango/dsr.py`

### Migration Impact

For controller developers:
1. Can now override `initialise()` for async setup on main event loop
2. `connect()` continues to work as before for device connection logic
3. Clear lifecycle: `initialise()` runs first, then `connect()` as initial task

For backend developers:
1. Backends now inherit from Backend base class
2. Constructor signature changed: accepts Controller, not Mapping
3. Implement `_run()` method instead of managing full initialization
4. Access `self._context` for dispatcher, controller, and mapping

Example transformation:
```python
# Before
class EpicsBackend:
    def __init__(self, mapping: Mapping):
        dispatcher = AsyncioDispatcher()
        backend = Backend(mapping, dispatcher.loop)
        backend.run_initial_tasks()

# After
class EpicsBackend(Backend):
    def __init__(self, controller: Controller, pv_prefix: str):
        super().__init__(controller)  # Handles initialization
        self._ioc = EpicsIOC(pv_prefix, self._mapping)

    def _run(self):
        self._ioc.run(self._dispatcher, self._context)
```

### Architectural Impact

This established a clear, consistent initialization pattern across all FastCS backends:

```
Backend.__init__:
  1. Create AsyncioDispatcher (main event loop)
  2. Run controller.initialise() on main event loop ← NEW
  3. Create Mapping from controller
  4. Link process tasks
  5. Prepare context

Backend.run():
  6. Run initial tasks (controller.connect(), etc.)
  7. Start scan tasks
  8. Call subclass._run() for protocol-specific execution
```

The addition of `controller.initialise()` on the main event loop enabled controllers to perform complex async setup operations before their API was exposed, while maintaining a clean separation between framework infrastructure and protocol implementations.
