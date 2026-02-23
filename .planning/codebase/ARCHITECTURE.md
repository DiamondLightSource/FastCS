# Architecture

**Analysis Date:** 2026-02-23

## Pattern Overview

**Overall:** Plugin-based Controller/Transport separation with async event loop at center

**Key Characteristics:**
- A `Controller` tree models a device (attributes + sub-controllers + methods) independently of any control system protocol
- A `ControllerAPI` is a read-only mirror of the controller tree built at startup and passed to transports
- Multiple `Transport` implementations (EPICS CA, EPICS PVA, REST, GraphQL, Tango) consume the same `ControllerAPI` and expose it over their respective protocols concurrently
- All runtime operations (scan loops, initial reads, transport serving) run on a single `asyncio` event loop
- The `launch` helper provides a CLI entry point backed by Pydantic/YAML config and `typer`

## Layers

**Domain Layer — Controllers:**
- Purpose: Implement device-specific logic; define attributes, scan methods, and commands; manage connection lifecycle
- Location: `src/fastcs/controllers/`
- Contains: `BaseController`, `Controller`, `ControllerVector`; user-defined subclasses go here or in driver packages
- Depends on: `fastcs.attributes`, `fastcs.methods`, `fastcs.connections`, `fastcs.datatypes`
- Used by: `FastCS` (via `ControllerAPI`), transport layer (indirectly through `ControllerAPI`)

**Attribute Layer:**
- Purpose: Typed, access-mode-aware data holders (`AttrR`, `AttrW`, `AttrRW`) with callback chains for read/write events
- Location: `src/fastcs/attributes/`
- Contains: `Attribute` ABC, `AttrR`, `AttrW`, `AttrRW`, `AttributeIO`, `AttributeIORef`, `HintedAttribute`
- Depends on: `fastcs.datatypes`, `fastcs.tracer`
- Used by: controllers (declare attributes), transport layer (reads current value, calls `put`)

**Datatype Layer:**
- Purpose: Map Python/numpy types to named FastCS types with metadata and validation
- Location: `src/fastcs/datatypes/`
- Contains: `DataType` ABC, `Int`, `Float`, `Bool`, `String`, `Enum`, `Waveform`, `Table`
- Depends on: `numpy`
- Used by: attributes (parameterised by datatype), transport layer (maps to protocol-specific types)

**Method Layer:**
- Purpose: Wrap async controller methods as bound `Command` (one-shot) or `Scan` (periodic) objects
- Location: `src/fastcs/methods/`
- Contains: `Command`, `UnboundCommand`, `Scan`, `UnboundScan`, `@command` / `@scan` decorators
- Depends on: `fastcs.tracer`
- Used by: controllers (register via decorators), `ControllerAPI` (schedules scan loops)

**API Layer — ControllerAPI:**
- Purpose: Immutable tree representation of a controller's public interface, consumed by transports
- Location: `src/fastcs/transports/controller_api.py`
- Contains: `ControllerAPI` dataclass; `walk_api()` iterator; scan/initial coroutine scheduling
- Depends on: `fastcs.attributes`, `fastcs.methods`
- Used by: `FastCS` (builds it), every transport (`connect` receives it)

**Transport Layer:**
- Purpose: Map `ControllerAPI` onto a specific protocol (EPICS, REST, GraphQL, Tango)
- Location: `src/fastcs/transports/`
- Contains: `Transport` ABC; `EpicsCATransport`, `EpicsPVATransport`, `RestTransport`, `GraphQLTransport`, `TangoTransport`
- Depends on: `fastcs.transports.controller_api`; protocol libraries (`softioc`, `p4p`, `fastapi`, `uvicorn`, `PyTango`)
- Used by: `FastCS` (calls `connect` then `serve` per transport)

**Connection Layer:**
- Purpose: Reusable async I/O primitives for driver code (TCP stream, serial)
- Location: `src/fastcs/connections/`
- Contains: `IPConnection`, `StreamConnection`, `IPConnectionSettings`, `SerialConnection`, `SerialConnectionSettings`
- Depends on: `asyncio`, `aioserial`
- Used by: controller implementations that need hardware I/O

**Application Entry Points:**
- Purpose: Tie everything together; provide `FastCS` class and `launch` CLI helper
- Location: `src/fastcs/control_system.py`, `src/fastcs/launch.py`
- Contains: `FastCS`, `launch`, `build_controller_api`; YAML/Pydantic config parsing via `typer`
- Depends on: all layers above
- Used by: end-user driver packages (`if __name__ == "__main__": launch(MyController)`)

## Data Flow

**Startup:**

1. User calls `launch(MyController)` (or instantiates `FastCS(controller, transports)` directly)
2. `launch` introspects controller `__init__` type hints, builds a Pydantic model from the YAML config, instantiates `controller` and `transports`
3. `FastCS.serve()` calls `controller.initialise()` (async hook for dynamic attribute creation) then `controller.post_initialise()` (validates type hints, connects `AttributeIO` callbacks)
4. `build_controller_api(controller)` recursively visits the controller tree and produces a `ControllerAPI` tree
5. For each transport: `transport.connect(controller_api, loop)` binds transport internals to the API
6. Scan coroutines from `controller_api.get_scan_and_initial_coros()` are started as `asyncio` tasks
7. Initial coroutines (scan methods with `period=ONCE`) are awaited once
8. All transport `.serve()` coroutines, plus an optional IPython interactive shell, are gathered on the event loop

**Read Path (attribute updated from hardware):**

1. A periodic `asyncio` task calls an `AttributeIO.update(attr)` callback
2. `AttributeIO.update` reads the hardware value and calls `await attr.update(new_value)`
3. `attr.update` validates the value (via `DataType.validate`), caches it, fires `on_update_callbacks`
4. Each transport's `on_update_callback` (e.g., `record.set(value)` for EPICS CA) publishes to the protocol layer

**Write Path (client writes a value):**

1. A transport receives a write (e.g., EPICS CA `on_update`, REST `PUT /{route}`)
2. Transport calls `await attribute.put(value)`
3. `AttrW.put` validates the value, calls `_on_put_callback` (which is `AttributeIO.send`)
4. `AttributeIO.send` sends the command to the hardware
5. If `sync_setpoint=True`, `_sync_setpoint_callbacks` are fired (e.g., updating the EPICS setpoint record without re-processing)

**Command Execution:**

1. Transport receives a command trigger (EPICS CA `Action` PV, REST `PUT /command-name`)
2. Transport calls `await command.fn()`
3. `Command.fn` wraps the bound controller method with exception logging

**State Management:**

- All attribute values are cached in-memory in each `AttrR` instance (`self._value`)
- No shared mutable state between controller and transports beyond the attribute objects
- Concurrent access to connections is serialised with `asyncio.Lock` in `StreamConnection` and `SerialConnection`

## Key Abstractions

**`Attribute[DType_T, AttributeIORefT]`:**
- Purpose: Typed, named, path-aware data point on a controller; holds current value and callback chains
- Examples: `src/fastcs/attributes/attr_r.py`, `src/fastcs/attributes/attr_w.py`, `src/fastcs/attributes/attr_rw.py`
- Pattern: Generic over datatype (`DType_T`) and IO reference (`AttributeIORefT`); `AttrR` adds read callbacks, `AttrW` adds write callbacks, `AttrRW` inherits both

**`AttributeIORef`:**
- Purpose: Protocol-agnostic specification of which part of a hardware API an attribute corresponds to
- Examples: `src/fastcs/demo/controllers.py` defines `TemperatureControllerAttributeIORef(name="R")`
- Pattern: Subclass `AttributeIORef`, add fields that identify the hardware endpoint; pair with a matching `AttributeIO` subclass

**`AttributeIO[DType_T, AttributeIORefT]`:**
- Purpose: Bridge between `Attribute` callbacks and actual hardware I/O
- Examples: `src/fastcs/demo/controllers.py` defines `TemperatureControllerAttributeIO`
- Pattern: Subclass `AttributeIO` parameterised with a concrete `AttributeIORef`; implement `async update(attr)` and `async send(attr, value)`

**`Controller`:**
- Purpose: Tree node in device model; class-level `Attribute`/`Method` declarations auto-bound at `__init__` via `__setattr__` override
- Examples: `src/fastcs/controllers/controller.py`, `src/fastcs/demo/controllers.py`
- Pattern: Declare class-level typed attributes (`ramp_rate = AttrRW(Float())`); add sub-controllers via `add_sub_controller`; override `connect`/`disconnect` for lifecycle; decorate methods with `@command()` or `@scan(period)`

**`ControllerVector`:**
- Purpose: Homogeneous indexed collection of `Controller` instances (e.g., a set of identical channels)
- Examples: `src/fastcs/controllers/controller_vector.py`
- Pattern: `MutableMapping[int, Controller]`; assign controllers by integer key (`vector[1] = Controller()`)

**`Transport`:**
- Purpose: Protocol adapter that maps `ControllerAPI` onto a specific control-system protocol
- Examples: `src/fastcs/transports/epics/ca/transport.py`, `src/fastcs/transports/rest/transport.py`
- Pattern: Subclass `Transport` dataclass; implement `connect(controller_api, loop)` and `async serve()`; optionally expose `context` for IPython shell

**`DataType`:**
- Purpose: Maps a Python/numpy type to a named FastCS type with validation metadata
- Examples: `src/fastcs/datatypes/int.py`, `src/fastcs/datatypes/float.py`, `src/fastcs/datatypes/string.py`
- Pattern: Frozen dataclass inheriting `DataType[T]`; implement `dtype`, `initial_value`; override `validate` for coercion

## Entry Points

**`launch(controller_class, version)`:**
- Location: `src/fastcs/launch.py`
- Triggers: `if __name__ == "__main__": launch(MyController)` in a driver package
- Responsibilities: Introspects controller `__init__` type hints, builds a Pydantic+typer CLI, parses YAML config, configures logging, instantiates controller and transports, runs `FastCS`

**`FastCS(controller, transports)`:**
- Location: `src/fastcs/control_system.py`
- Triggers: Direct programmatic use or via `launch`
- Responsibilities: Builds `ControllerAPI`, starts scan tasks, connects transports, gathers all async coroutines on the event loop, handles SIGINT/SIGTERM gracefully

**`Demo module`:**
- Location: `src/fastcs/demo/__main__.py`
- Triggers: `python -m fastcs.demo`
- Responsibilities: Runs `TemperatureController` as a demo of FastCS patterns including IO, scan, commands, and sub-controllers

## Error Handling

**Strategy:** Exceptions in scan loops and commands are caught, logged, and re-raised (stopping the affected loop). The main asyncio gather handles `CancelledError` for clean shutdown.

**Patterns:**
- `Command.fn` and `Scan.fn` wrap the underlying callable in a try/except that logs via `fastcs.logging.logger`
- `AttrR.update` logs but re-raises exceptions from `on_update_callbacks`
- `AttrW.put` logs but swallows exceptions from `_on_put_callback` and `_sync_setpoint_callbacks`
- `FastCS.serve` catches `asyncio.CancelledError` (clean shutdown) and logs `Exception` (unhandled)
- `LaunchError` and `FastCSError` in `src/fastcs/exceptions.py` for configuration-time failures

## Cross-Cutting Concerns

**Logging:** `loguru`-based singleton logger in `src/fastcs/logging/__init__.py`; structured key-value kwargs; optional Graylog UDP sink; all modules call `bind_logger(logger_name=__name__)` to get a named wrapper; `intercept_std_logger` re-routes third-party stdlib loggers

**Tracing:** `Tracer` mixin at `src/fastcs/tracer.py`; per-instance opt-in verbose logging at `TRACE` level; supports key-value filters; inherited by `Attribute`, `BaseController`, `AttributeIO`, `Method`

**Validation:** `DataType.validate` coerces incoming values at both read (`AttrR.update`) and write (`AttrW.put`) boundaries; `BaseController._validate_type_hints` checks declared type hints match assigned attributes at startup; `BaseController._validate_io` ensures one-to-one `AttributeIO`-to-`AttributeIORef` mapping

**Authentication:** Not present — no auth layer in any transport

---

*Architecture analysis: 2026-02-23*
