# 7. Merge TransportAdapter and TransportOptions into Transport

Date: 2025-09-29

**Related:** [PR #220](https://github.com/DiamondLightSource/FastCS/pull/220)

## Status

Accepted

## Context

Following the Backend-to-Transport refactoring (ADR-0004), FastCS transports were implemented using two separate class hierarchies: `TransportAdapter` for the transport implementation and separate `*Options` classes for configuration.

**Original Architecture - Two-Class Pattern:**

Each transport required two classes:

```python
# Configuration class
@dataclass
class EpicsPVAOptions:
    pv_prefix: str
    gui_dir: Path | None = None

# Implementation class
class EpicsPVATransport(TransportAdapter):
    def __init__(
        self,
        controller_api: ControllerAPI,
        options: EpicsPVAOptions,
    ):
        self._controller_api = controller_api
        self._options = options
        # ... setup code

    async def run(self):
        # ... transport-specific code
```

**Usage Pattern:**
```python
# Create options
options = EpicsPVAOptions(pv_prefix="MY:DEVICE:")

# Pass options to FastCS
fastcs = FastCS(controller, [options])

# FastCS internally:
# - Matched options type
# - Created corresponding TransportAdapter
# - Passed options to adapter
```

**Problems with Two-Class Pattern:**

1. **API Surface Duplication:** Two classes per transport (5 transports = 10 classes) when a single class could suffice.

2. **Complex Instantiation Logic:** FastCS needed pattern matching logic to create the right adapter from options:
   ```python
   match option:
       case EpicsPVAOptions():
           transport = EpicsPVATransport(controller_api, option)
       case EpicsCAOptions():
           transport = EpicsCATransport(controller_api, loop, option)
       # ... 5 more cases
   ```

3. **Inconsistent Constructor Signatures:** Different transports had different initialization requirements:
   - Some needed `loop`, others didn't
   - Some needed `controller_api` immediately, others deferred it
   - Options were passed separately, requiring attribute access: `self._options.pv_prefix`

4. **Unnecessary Abstraction Layer:** The Options classes were simple dataclasses with no behavior - they existed solely to carry configuration to the adapter

The system needed a simpler, more direct approach where transport configuration and implementation were unified.

## Decision

We merged `TransportAdapter` and `*Options` classes into a single `Transport` base class that combines configuration and implementation.

### New Architecture

**Unified Transport Class:**

```python
@dataclass
class EpicsPVATransport(Transport):
    epicspva: EpicsIOCOptions

    def connect(
        self, controller_api: ControllerAPI, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._controller_api = controller_api
        self._loop = loop
        self._ioc = EpicsPVAIOC(
            pv_prefix=self.epicspva.pv_prefix,
            controller_api=controller_api,
        )

    async def serve(self) -> None:
        await self._ioc.run(self.epicspva)
```

### Key Changes

1. **Single Class per Transport:**
   - Merged adapter and options into one dataclass
   - Configuration fields are direct attributes
   - Implementation methods are instance methods

2. **Standardized Initialization:**
   - All transports use `@dataclass` for configuration
   - `connect()` receives controller_api and loop (deferred initialization)
   - `serve()` runs the transport server
   - Consistent signature across all transports

3. **Simplified FastCS:**
   ```python
   # Before: Options → Adapter matching logic
   for option in transport_options:
       match option:
           case EpicsPVAOptions():
               transport = EpicsPVATransport(controller_api, option)

   # After: Direct transport instances
   for transport in transports:
       transport.connect(controller_api, loop)  # Unified interface
   ```

4. **Better Type Safety:**
   - `Transport.union()` creates Union type of all transports
   - Used for CLI type hints and validation
   - Automatically updated when new transports are added

5. **Cleaner Imports:**
   ```python
   # Before
   from fastcs.transport.epics.pva.options import EpicsPVAOptions
   options = EpicsPVAOptions(pv_prefix="MY:DEVICE:")

   # After
   from fastcs.transports.epics.pva import EpicsPVATransport
   transport = EpicsPVATransport(epicspva=EpicsIOCOptions(pv_prefix="MY:DEVICE:"))
   ```

### Benefits

- **Reduced API Surface:** 5 classes instead of 10 (one Transport per protocol, not one Adapter + one Options)

- **Simpler Mental Model:** Configuration and implementation in one place

- **Consistent Interface:** All transports follow same initialization pattern

- **Less Boilerplate:** No pattern matching needed in FastCS

- **Easier Maintenance:** Transport parameters defined once in dataclass fields

- **Better Type Safety:** Automatic Union type generation for all transports

- **Cleaner Usage:** Direct instantiation of transport with configuration

## Consequences

### Technical Changes

- 87 insertions, 87 deletions across 16 files (net neutral, massive simplification)
- Renamed `src/fastcs/transport/adapter.py` → `src/fastcs/transport/transport.py`
- Merged all `*Options` classes into corresponding `*Transport` classes
- Simplified `src/fastcs/launch.py` by removing pattern matching logic
- Updated all transport implementations:
  - `src/fastcs/transport/epics/ca/adapter.py`
  - `src/fastcs/transport/epics/pva/adapter.py`
  - `src/fastcs/transport/graphql/adapter.py`
  - `src/fastcs/transport/rest/adapter.py`
  - `src/fastcs/transport/tango/adapter.py`
- Updated all tests and examples

### Migration Impact

For transport users:

**Before (Options pattern):**
```python
from fastcs.transport.epics.pva.options import EpicsPVAOptions
from fastcs import FastCS

options = EpicsPVAOptions(
    pv_prefix="MY:DEVICE:",
    gui_dir=Path("gui")
)

fastcs = FastCS(controller, [options])
```

**After (Transport pattern):**
```python
from fastcs.transports.epics.pva import EpicsPVATransport
from fastcs.transports.epics import EpicsIOCOptions
from fastcs import FastCS

transport = EpicsPVATransport(
    epicspva=EpicsIOCOptions(
        pv_prefix="MY:DEVICE:",
        gui_dir=Path("gui")
    )
)

fastcs = FastCS(controller, [transport])
```

For transport developers:

**Before (Two classes):**
```python
@dataclass
class MyOptions:
    param1: str
    param2: int = 42

class MyTransport(TransportAdapter):
    def __init__(self, controller_api: ControllerAPI, options: MyOptions):
        self._options = options
        # Setup using self._options.param1

    async def run(self):
        # Implementation
```

**After (One class):**
```python
@dataclass
class MyTransport(Transport):
    param1: str
    param2: int = 42

    def connect(self, controller_api: ControllerAPI, loop: asyncio.AbstractEventLoop):
        self._controller_api = controller_api
        # Setup using self.param1 directly

    async def serve(self):
        # Implementation
```

### Architectural Impact

This decision established a cleaner, more direct API for transport implementations, reducing complexity while maintaining full functionality. The unified Transport class became the single abstraction for all protocol implementations in FastCS.
