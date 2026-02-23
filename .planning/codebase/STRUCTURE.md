# Codebase Structure

**Analysis Date:** 2026-02-23

## Directory Layout

The repository root contains:
- `src/fastcs/` — the main library package
- `tests/` — pytest test suite
- `docs/` — Sphinx documentation source
- `build/` — generated Sphinx HTML (committed for GitHub Pages)
- `pyproject.toml` — project metadata, dependencies, tool config
- `codecov.yaml` — coverage config
- `.github/` — CI/CD workflows, issue/PR templates

`src/fastcs/` internal structure:

- `__init__.py` — Public API: `FastCS`, `launch`, `ONCE`, `__version__`
- `_version.py` — Generated version string (setuptools_scm)
- `control_system.py` — `FastCS` class, `build_controller_api`
- `launch.py` — CLI entry point helper (typer + Pydantic + YAML)
- `tracer.py` — `Tracer` mixin for opt-in verbose logging
- `util.py` — `ONCE` sentinel, `snake_to_pascal`
- `exceptions.py` — `FastCSError`, `LaunchError`
- `attributes/` — Attribute types and IO abstractions
- `controllers/` — Controller base classes
- `datatypes/` — DataType definitions
- `methods/` — Command and Scan method wrappers
- `connections/` — Hardware I/O primitives (TCP, serial)
- `logging/` — Loguru-based structured logging
- `transports/` — Protocol adapters (EPICS CA, EPICS PVA, REST, GraphQL, Tango)
- `demo/` — Reference device driver implementation

`src/fastcs/attributes/` contains:
- `__init__.py`
- `attribute.py` — `Attribute` ABC (generic, access-mode-aware)
- `attr_r.py` — `AttrR` (read-only attribute)
- `attr_w.py` — `AttrW` (write-only attribute)
- `attr_rw.py` — `AttrRW` (read-write, inherits both)
- `attribute_io.py` — `AttributeIO` ABC
- `attribute_io_ref.py` — `AttributeIORef` base dataclass
- `hinted_attribute.py` — `HintedAttribute` for type-hint introspection
- `util.py` — `PredicateEvent`, `AttrValuePredicate`

`src/fastcs/controllers/` contains:
- `__init__.py`
- `base_controller.py` — `BaseController` (binding, introspection, `__setattr__` override)
- `controller.py` — `Controller` (named sub-controllers)
- `controller_vector.py` — `ControllerVector` (indexed sub-controllers)

`src/fastcs/datatypes/` contains:
- `__init__.py`
- `datatype.py` — `DataType` ABC, `DType` union, `DType_T` TypeVar
- `_numeric.py` — Shared `_Numeric` base for `Int` and `Float`
- `int.py`, `float.py`, `bool.py`, `string.py`, `enum.py`, `waveform.py`, `table.py`
- `_util.py` — `numpy_to_fastcs_datatype` helper

`src/fastcs/methods/` contains:
- `__init__.py`
- `method.py` — `Method` ABC, `MethodCallback` type
- `command.py` — `Command`, `UnboundCommand`, `@command` decorator
- `scan.py` — `Scan`, `UnboundScan`, `@scan` decorator

`src/fastcs/connections/` contains:
- `__init__.py`
- `ip_connection.py` — `IPConnection`, `StreamConnection`, `IPConnectionSettings`
- `serial_connection.py` — `SerialConnection`, `SerialConnectionSettings`

`src/fastcs/logging/` contains:
- `__init__.py` — singleton logger, `bind_logger`, `configure_logging`, `intercept_std_logger`
- `_logging.py` — `_configure_logger`, `LogLevel`, `LoguruGelfUdpHandler`
- `_graylog.py` — `GraylogEndpoint`, `GraylogStaticFields`, `GraylogEnvFields`

`src/fastcs/transports/` contains:
- `__init__.py` — re-exports all transports with `try/except ImportError` guards
- `transport.py` — `Transport` ABC
- `controller_api.py` — `ControllerAPI` dataclass, scan scheduling
- `epics/` — shared EPICS options, docs, GUI; sub-packages `ca/` (softioc) and `pva/` (p4p)
- `rest/` — FastAPI + uvicorn transport
- `graphql/` — GraphQL transport
- `tango/` — PyTango transport

`src/fastcs/transports/epics/` contains:
- `__init__.py`
- `options.py` — `EpicsIOCOptions`, `EpicsGUIOptions`, `EpicsDocsOptions`
- `docs.py` — `EpicsDocs` (RST docs generation)
- `gui.py` — `EpicsGUI` (EDL/BOB GUI generation)
- `util.py` — `controller_pv_prefix` helper
- `ca/` — `EpicsCATransport`, `EpicsCAIOC` (PV creation, PVI metadata), cast utilities
- `pva/` — `EpicsPVATransport`, `P4PIOC`, `_pv_handlers.py`, `pvi.py`, `gui.py`, `types.py`

`tests/` mirrors `src/fastcs/` structure:
- Top-level unit tests: `test_attributes.py`, `test_controllers.py`, `test_control_system.py`, `test_datatypes.py`, `test_launch.py`, `test_methods.py`, `test_util.py`, `test_docs_snippets.py`
- `transports/epics/ca/` — EPICS CA tests
- `transports/epics/pva/` — EPICS PVA tests
- `transports/rest/` — REST tests
- `transports/graphQL/` — GraphQL tests
- `transports/tango/` — Tango tests
- `benchmarking/` — performance benchmarks
- `assertable_controller.py` — shared test-helper controller
- `example_softioc.py`, `example_p4p_ioc.py` — example IOC scripts for integration tests

## Directory Purposes

**`src/fastcs/`:**
- Purpose: The library package; everything importable by downstream driver packages
- Contains: Core classes, transport adapters, connection helpers, logging, demo
- Key files: `__init__.py` (public surface), `control_system.py` (main class), `launch.py` (CLI)

**`src/fastcs/attributes/`:**
- Purpose: All attribute types and IO abstraction classes
- Contains: `Attribute` ABC, `AttrR/W/RW`, `AttributeIO`, `AttributeIORef`, `HintedAttribute`
- Key files: `attribute.py`, `attr_r.py`, `attr_w.py`, `attr_rw.py`, `attribute_io.py`, `attribute_io_ref.py`

**`src/fastcs/controllers/`:**
- Purpose: Base classes for device controllers; all binding and introspection logic lives here
- Contains: `BaseController`, `Controller`, `ControllerVector`
- Key files: `base_controller.py`

**`src/fastcs/datatypes/`:**
- Purpose: FastCS-typed wrappers for Python/numpy types with validation metadata
- Contains: `DataType` ABC and all concrete types
- Key files: `datatype.py`, `int.py`, `float.py`, `string.py`, `enum.py`, `waveform.py`, `table.py`

**`src/fastcs/methods/`:**
- Purpose: Decorators and wrappers for async controller methods
- Contains: `Command`, `UnboundCommand`, `Scan`, `UnboundScan`, `@command`, `@scan`
- Key files: `command.py`, `scan.py`

**`src/fastcs/connections/`:**
- Purpose: Reusable async hardware I/O primitives for use in `Controller` implementations
- Contains: TCP stream and serial helpers
- Key files: `ip_connection.py`, `serial_connection.py`

**`src/fastcs/transports/`:**
- Purpose: All protocol adapters; each sub-package handles one control-system protocol
- Contains: `Transport` ABC, `ControllerAPI`, four transport implementations
- Key files: `transport.py`, `controller_api.py`

**`src/fastcs/transports/epics/ca/`:**
- Purpose: EPICS Channel Access transport using `softioc`
- Key files: `transport.py` (`EpicsCATransport`), `ioc.py` (PV creation + PVI)

**`src/fastcs/transports/epics/pva/`:**
- Purpose: EPICS PV Access transport using `p4p`
- Key files: `transport.py` (`EpicsPVATransport`), `ioc.py` (`P4PIOC`), `_pv_handlers.py`

**`src/fastcs/transports/rest/`:**
- Purpose: HTTP REST transport using FastAPI + uvicorn
- Key files: `transport.py` (`RestTransport`), `rest.py` (`RestServer`, route building)

**`src/fastcs/transports/graphql/`:**
- Purpose: GraphQL transport
- Key files: `transport.py` (`GraphQLTransport`), `graphql.py` (`GraphQLServer`)

**`src/fastcs/transports/tango/`:**
- Purpose: Tango Controls transport using PyTango
- Key files: `transport.py` (`TangoTransport`), `dsr.py` (`TangoDSR`)

**`src/fastcs/demo/`:**
- Purpose: Reference implementation demonstrating all major FastCS patterns
- Contains: `TemperatureController`, `TemperatureRampController`, simulated device backend
- Key files: `controllers.py`, `__main__.py`, `simulation/device.py`

**`src/fastcs/logging/`:**
- Purpose: Loguru-based structured logging with optional Graylog sink
- Key files: `__init__.py` (singleton logger, `configure_logging`, `bind_logger`), `_logging.py`

**`tests/`:**
- Purpose: Pytest test suite mirroring the src package structure
- Contains: Unit tests for core modules, integration tests per transport, benchmarks
- Key files: `conftest.py`, `assertable_controller.py`, `util.py`

## Key File Locations

**Entry Points:**
- `src/fastcs/__init__.py` — Public API (`FastCS`, `launch`, `ONCE`)
- `src/fastcs/control_system.py` — `FastCS` class and `build_controller_api`
- `src/fastcs/launch.py` — `launch()`, `_extract_options_model`, YAML/CLI wiring
- `src/fastcs/demo/__main__.py` — Demo device entry point (`python -m fastcs.demo`)

**Configuration:**
- `pyproject.toml` — All project metadata, dependency groups, tool config (ruff, mypy, pytest)
- `codecov.yaml` — Coverage gating configuration

**Core Logic:**
- `src/fastcs/controllers/base_controller.py` — Attribute binding, `__setattr__` override, type-hint introspection, `AttributeIO` connection
- `src/fastcs/transports/controller_api.py` — `ControllerAPI`, scan scheduling, `walk_api()`
- `src/fastcs/attributes/attr_r.py` — Read attribute with update callbacks and predicate-wait support
- `src/fastcs/attributes/attr_w.py` — Write attribute with put callback and sync setpoint callbacks
- `src/fastcs/attributes/attribute_io.py` — `AttributeIO` ABC defining the hardware bridge interface
- `src/fastcs/attributes/attribute_io_ref.py` — `AttributeIORef` base dataclass

**Testing:**
- `tests/conftest.py` — Shared pytest fixtures
- `tests/assertable_controller.py` — Test-helper controller with assertable attributes
- `tests/test_control_system.py` — Tests for `FastCS` startup/shutdown lifecycle
- `tests/transports/epics/ca/test_softioc.py` — EPICS CA transport tests

## Naming Conventions

**Files:**
- Snake_case for all Python modules: `base_controller.py`, `attribute_io_ref.py`
- Private modules prefixed with underscore: `_numeric.py`, `_logging.py`, `_graylog.py`, `_pv_handlers.py`
- Transport sub-packages named after the protocol: `ca/`, `pva/`, `rest/`, `graphql/`, `tango/`
- Test files prefixed with `test_`: `test_attributes.py`, `test_launch.py`

**Classes:**
- PascalCase throughout: `BaseController`, `ControllerVector`, `AttributeIORef`, `EpicsCATransport`
- Attribute classes use abbreviated access-mode suffix: `AttrR`, `AttrW`, `AttrRW`
- Transport classes use protocol name plus `Transport` suffix: `EpicsCATransport`, `RestTransport`, `TangoTransport`
- DataType classes use the concept name directly: `Int`, `Float`, `String`, `Waveform`

**Functions and methods:**
- Snake_case: `add_sub_controller`, `build_controller_api`, `snake_to_pascal`
- Private helpers prefixed with `_`: `_bind_attrs`, `_validate_type_hints`, `_create_and_link_attribute_pvs`

**TypeVars and type aliases:**
- PascalCase with `_T` suffix: `DType_T`, `AttributeIORefT`, `Controller_T`

**Decorators:**
- Lowercase matching the concept: `@command()`, `@scan(period)`

## Where to Add New Code

**New Controller / Device Driver:**
- Primary code: New Python package outside this repo, or under `src/fastcs/demo/` for examples
- Subclass `Controller` from `src/fastcs/controllers/controller.py`
- Declare class-level `AttrR/W/RW` attributes and `@command`/`@scan` methods
- Subclass `AttributeIORef` from `src/fastcs/attributes/attribute_io_ref.py` for hardware mapping
- Subclass `AttributeIO` from `src/fastcs/attributes/attribute_io.py` for hardware I/O
- Tests: Mirror structure under `tests/` or in the driver package tests

**New DataType:**
- Implementation: `src/fastcs/datatypes/<name>.py`
- Export: Add to `src/fastcs/datatypes/__init__.py`
- Pattern: Frozen dataclass inheriting `DataType[T]`; implement `dtype` and `initial_value`; override `validate` if needed

**New Transport:**
- Implementation: New sub-package `src/fastcs/transports/<name>/`
- Required files: `transport.py` (subclass `Transport` dataclass), `options.py` (options dataclass), implementation module
- Export: Add optional import in `src/fastcs/transports/__init__.py` guarded with `try/except ImportError`
- Tests: `tests/transports/<name>/test_<name>.py`

**New Attribute Utility:**
- Shared helpers: `src/fastcs/attributes/util.py`
- New attribute behaviour: Extend `src/fastcs/attributes/attr_r.py` or `src/fastcs/attributes/attr_w.py`

**General Utilities:**
- Cross-cutting helpers: `src/fastcs/util.py`
- Module-specific helpers follow the pattern of `src/fastcs/transports/rest/util.py`

## Special Directories

**`build/`:**
- Purpose: Generated Sphinx HTML documentation output
- Generated: Yes (by `sphinx-build`)
- Committed: Yes (served via GitHub Pages)

**`src/fastcs/demo/simulation/`:**
- Purpose: Software simulator for the demo device; used in integration tests and demo runs
- Generated: No
- Committed: Yes

**`.github/`:**
- Purpose: GitHub Actions CI/CD, issue templates, PR templates, GitHub Pages version switcher
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-02-23*
