# 6. Create ControllerAPI Abstraction Layer

Date: 2025-03-10

**Related:** [PR #87](https://github.com/DiamondLightSource/FastCS/pull/87)

## Status

Accepted

## Context

In the original FastCS architecture, transport implementations (EPICS CA, PVA, REST, GraphQL, Tango) directly accessed `Controller` and `SubController` instances to extract attributes, methods, and metadata for serving over their respective protocols.

**Original Architecture - Direct Controller Access:**
- Each transport was responsible for traversing the controller and its sub-controllers to find attributes and methods
- Transports had direct access to controller internals, allowing them to modify things they shouldn't
- Each transport implemented its own custom traversal logic
- No static, immutable view of what a controller exposes

**Problems with Direct Coupling:**

1. **Tight Coupling:** Transports were tightly coupled to the internal structure of `Controller` and `SubController` classes, making it difficult to evolve the controller implementation without breaking transports

2. **Code Duplication:** Every transport re-implemented similar logic to:
   - Traverse the controller/sub-controller tree
   - Discover attributes and methods
   - Build hierarchical structures for their protocol
   - Handle naming and path construction

3. **No Encapsulation:** Transports had direct access to mutable controller state, making it possible to inadvertently modify things they shouldn't be able to change

4. **No Static View:** Controllers expose their API dynamically during traversal rather than providing a complete, static snapshot after initialization

The system needed a way to:
- Provide a complete, static view of the controller API once it's fully initialized
- Prevent transports from having direct access to mutable controller internals
- Decouple transport implementations from controller internals
- Provide a consistent view of controller APIs across all transports
- Centralize the logic for extracting and organizing controller metadata

## Decision

We introduced `ControllerAPI` as an abstraction layer that sits between `Controller` instances and transport implementations.

### New Architecture

**ControllerAPI - Transport-Independent Representation:**
```python
@dataclass
class ControllerAPI:
    path: list[str]
    attributes: dict[str, Attribute]
    command_methods: dict[str, Command]
    put_methods: dict[str, Put]
    scan_methods: dict[str, Scan]
    sub_apis: dict[str, "ControllerAPI"]
    description: str | None

    def walk_api(self) -> Iterator["ControllerAPI"]:
        """Traverse the entire API tree"""
```

### Key Changes

1. **API Extraction Centralized:**
   - A single `create_controller_api()` function extracts the API from a Controller
   - This function handles all traversal, method discovery, and hierarchy building
   - All transports use the same API extraction logic

2. **Transports Accept ControllerAPI:**
   - **Before:** `EpicsCAIOC(pv_prefix, controller: Controller)`
   - **After:** `EpicsCAIOC(pv_prefix, controller_api: ControllerAPI)`
   - Transports no longer have direct access to mutable Controller internals
   - ControllerAPI provides a static, read-only view of the controller's complete API

3. **Complete API After Initialization:**
   - Once a controller is fully initialized, its entire API (all sub-controllers, attributes, and methods) is exposed in `ControllerAPI`
   - Transports receive a complete snapshot rather than having to traverse dynamically
   - Changes to the controller after initialization don't affect the ControllerAPI

4. **Hierarchical API Structure:**
   - ControllerAPI contains nested `sub_apis` for sub-controllers, forming a tree structure
   - `walk_api()` method provides depth-first traversal
   - Each level includes its path for proper naming

5. **Complete Method Discovery:**
   - Separate dictionaries for command_methods, put_methods, scan_methods
   - Methods discovered and organized during API creation
   - Transports receive ready-to-use method metadata

### Benefits:

- **Static View After Initialization:** Once a controller is fully initialized, its entire API (all sub-controllers, attributes, and methods) is exposed in a complete, static snapshot

- **Encapsulation:** Transports cannot directly access or modify mutable controller internals - they work with a read-only ControllerAPI. The only attributes and methods themselves are mutable.

- **Separation of Concerns:**
  - Controllers focus on device logic
  - ControllerAPI handles API representation
  - Transports focus on protocol implementation

- **Single Source of Truth:** One canonical representation of what a controller exposes

- **Reduced Code Duplication:** Traversal and extraction logic written once

- **Testability:** Controllers can be tested with mock ControllerAPIs, transports can be tested with synthetic APIs

- **Evolution Independence:** Controller internals can change without affecting transports as long as API extraction is updated

## Consequences

### Technical Changes

- 1,009 insertions, 568 deletions across 32 files
- Created `src/fastcs/controller_api.py` with ControllerAPI dataclass
- Updated all transport adapters to accept ControllerAPI instead of Controller:
  - `src/fastcs/transport/epics/ca/adapter.py`
  - `src/fastcs/transport/epics/pva/adapter.py`
  - `src/fastcs/transport/graphQL/adapter.py`
  - `src/fastcs/transport/rest/adapter.py`
  - `src/fastcs/transport/tango/adapter.py`
- Refactored `src/fastcs/cs_methods.py` for method extraction
- Updated `src/fastcs/backend.py` to create ControllerAPI before passing to transports
- All transport IOC/server implementations updated to use ControllerAPI

### Migration Impact

For transport developers:
1. Update transport constructors to accept `ControllerAPI` instead of `Controller`
2. Replace direct attribute/method access with ControllerAPI dictionary lookups
3. Use `walk_api()` for tree traversal instead of custom logic
4. Remove custom extraction code in favor of ControllerAPI structure

For controller developers:
- No changes required - controllers continue to work as before
- ControllerAPI is created automatically by the backend

### Architectural Impact

This established a clean layered architecture:
```
Controllers (domain logic)
     ↓
ControllerAPI (canonical representation)
     ↓
Transports (protocol implementation)
```

The ControllerAPI became the primary contract between the FastCS core and transport implementations, ensuring all transports have a consistent, complete view of controller capabilities.
