# 4. Rename Backend to Transport

Date: 2024-11-29

**Related:** [PR #67](https://github.com/DiamondLightSource/FastCS/pull/67)

## Status

Accepted

## Context

In the original FastCS architecture, the term "backend" was used to describe both:
1. The overall framework/system that managed controllers (the "backend system")
2. The specific communication protocol implementations (EPICS CA, PVA, REST, Tango)

**Original Architecture:**
- There was a `Backend` base class that protocol implementations inherited from
- Protocol-specific classes like `EpicsBackend`, `RestBackend`, `TangoBackend` extended `Backend`
- Users worked directly with these inherited backend classes
- This created tight coupling between the core framework and protocol implementations

This dual usage of "backend" created confusion for developers and users:
- It was unclear whether "backend" referred to the framework itself or the protocol layer
- The terminology didn't clearly differentiate between the abstract framework and the underlying communication mechanisms
- The inheritance pattern made it difficult to compose multiple transports or swap them dynamically

## Decision

We renamed "backend" to "transport" for all protocol/communication implementations to clearly differentiate them from the abstract framework.

This refactoring involved:

1. **Terminology Change:**
   - `backends/` directory → `transport/` directory
   - `EpicsBackend` → `EpicsTransport`
   - `RestBackend` → `RestTransport`
   - `TangoBackend` → `TangoTransport`

2. **Architectural Improvements:**
   - Introduced `TransportAdapter` abstract base class defining the contract for all transports:
     - `run()` - Start the transport
     - `create_docs()` - Generate documentation
     - `create_gui()` - Generate GUI metadata
   - Split transport configuration into separate `options` modules
   - Added adapter pattern with template methods for consistency

3. **Plugin Architecture (Composition over Inheritance):**
   - **Before:** `Backend` base class with `EpicsBackend`, `RestBackend`, etc. inheriting from it
   - **After:** `FastCS` core class that accepts `Transport` implementations as plugins
   - Transports are now passed to `FastCS` rather than being subclasses of a framework class
   - This enables flexible composition, runtime transport selection, and loose coupling

4. **Public API Restructuring:**
   - Introduced `FastCS` class as the programmatic interface for running controllers with transports
   - Added `launch()` function as the primary entry point for initializing controllers
   - Cleaned up import namespace to add structure to the public API

The term "backend" was reserved for referring to the overall FastCS framework/system, while "transport" specifically refers to protocol implementations (EPICS CA, PVA, REST, GraphQL, Tango).

## Consequences

- **Clearer Terminology:** The separation between framework (backend) and protocol layer (transport) is now explicit and unambiguous
- **Consistent Architecture:** All transports follow the adapter pattern with a standardized interface
- **Better Separation of Concerns:** Transport configuration is separated from transport implementation via options modules
- **Improved Extensibility:** Adding new transport protocols is more straightforward with the adapter pattern
- **Reduced Dependency Coupling:** Transport options can be imported without including heavy transport dependencies
- **Clearer Public API:** The `launch()` function and `FastCS` class provide clear entry points

### Migration Path

For users migrating from the old API:
1. Replace all `backend` imports with `transport` imports
2. Update class names (e.g., `EpicsBackend` → `EpicsTransport`)
3. Prefer using the new `launch()` function instead of directly instantiating transports
4. Update configuration to use transport-specific options dataclasses

### Technical Impact

- 681 insertions, 321 deletions across the codebase
- All transport implementations refactored to follow adapter pattern
- Transport options moved to separate modules for cleaner dependency management
- Mapping class functionality integrated into Controller

This decision established a clearer architectural foundation for FastCS, making it easier for contributors to understand the system's layers and for users to reason about how their controllers interact with different communication protocols.
