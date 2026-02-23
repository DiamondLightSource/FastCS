# Codebase Concerns

**Analysis Date:** 2026-02-23

## Tech Debt

**Use of Private CPython Typing Internals:**
- Issue: `base_controller.py` imports `_GenericAlias` from `typing`, a CPython implementation detail that is not part of the public API
- Files: `src/fastcs/controllers/base_controller.py:6`
- Impact: May break on non-CPython interpreters or future CPython versions without notice; suppressed with `# type: ignore`
- Fix approach: Replace with public introspection APIs (e.g., `typing.get_args`, `typing.get_origin`, or `types.GenericAlias`) to detect generic aliases

**Deprecated `asyncio.get_event_loop()` Usage:**
- Issue: `asyncio.get_event_loop()` is deprecated since Python 3.10 and will raise a `DeprecationWarning` (turned into errors by `filterwarnings = "error"` in pytest) in contexts where there is no current event loop
- Files: `src/fastcs/control_system.py:39`, `src/fastcs/launch.py:162`
- Impact: Creates ambiguity about which event loop is running; can break in Python 3.12+ where the behavior changed
- Fix approach: Replace with `asyncio.new_event_loop()` combined with explicit `asyncio.set_event_loop()`, or use `asyncio.run()` at the entry point

**`pvi` GUI Import with `# type: ignore`:**
- Issue: `from pvi._format.dls import DLSFormatter  # type: ignore` uses a private submodule of the `pvi` package with no type stubs
- Files: `src/fastcs/transports/epics/gui.py:1`
- Impact: Changes to `pvi` internals could silently break GUI generation; no type safety
- Fix approach: Work with `pvi` maintainers to expose `DLSFormatter` via a public API or pin a tested version more tightly

**REST Transport Command Routing Bug:**
- Issue: In `_add_command_api_routes`, the outer loop walks all controller APIs but the inner loop iterates `root_controller_api.command_methods` (the root) instead of `controller_api.command_methods` (the current node)
- Files: `src/fastcs/transports/rest/rest.py:153-165`
- Impact: Commands from sub-controllers are silently not registered in the REST API; commands are registered multiple times (once per sub-controller walked) with conflicting paths
- Fix approach: Change `root_controller_api.command_methods.items()` to `controller_api.command_methods.items()` on line 157

**Tango `max_alarm` Mapped to `min_alarm` Field:**
- Issue: In `DATATYPE_FIELD_TO_SERVER_FIELD`, the `max_alarm` key maps to `"min_alarm"` instead of `"max_alarm"`, meaning maximum alarm threshold is silently applied to the minimum alarm field in Tango
- Files: `src/fastcs/transports/tango/util.py:26`
- Impact: Tango attributes configured with `max_alarm` will behave incorrectly—upper alarm threshold is set as the lower alarm threshold
- Fix approach: Change `"max_alarm": "min_alarm"` to `"max_alarm": "max_alarm"` in the `DATATYPE_FIELD_TO_SERVER_FIELD` dict

**Demo Simulation Uses Bare `except`:**
- Issue: `handle_exceptions` wrapper in simulation device catches all exceptions including `KeyboardInterrupt` and `SystemExit`, then calls `os._exit(-1)` (bypassing all cleanup)
- Files: `src/fastcs/demo/simulation/device.py:34`
- Impact: Ungraceful shutdown; prevents Python finalizers and asyncio cleanup; masks programming errors during development
- Fix approach: Catch `Exception` instead of bare `except`; use `sys.exit()` instead of `os._exit()`; or propagate the exception and let the event loop handle shutdown

**`pydantic.v1` Compatibility Shim in Demo:**
- Issue: `src/fastcs/demo/simulation/device.py:9` imports from `pydantic.v1.dataclasses` (the legacy v1 compat shim) with a `# type: ignore` on the `TempController` class
- Files: `src/fastcs/demo/simulation/device.py:9`, `src/fastcs/demo/simulation/device.py:272`
- Impact: Pydantic v1 compatibility shim may be removed in future Pydantic versions; tickit library pinned to `~=0.4.3` which requires v1 types
- Fix approach: Track `https://github.com/DiamondLightSource/tickit/issues/212`; migrate when tickit supports Pydantic v2

**`_GenericAlias` Used for Type Argument Count Check:**
- Issue: `_find_type_hints` in `BaseController` checks `len(args) == 2` for `_GenericAlias` but provides no explanation; comment only says "e.g. AttrR[int]"
- Files: `src/fastcs/controllers/base_controller.py:76`
- Impact: Fragile; the check `len(args) == 2` is undocumented and will silently fail if FastCS attribute generics are ever extended beyond 2 type parameters
- Fix approach: Add documentation; check specifically for known two-parameter classes rather than generic `len(args) == 2`

## Known Bugs

**REST Sub-Controller Commands Not Registered:**
- Symptoms: Commands defined on sub-controllers are not accessible via the REST transport; root-level commands are registered N times (where N is sub-controller count + 1)
- Files: `src/fastcs/transports/rest/rest.py:153-165`
- Trigger: Any controller with sub-controllers that have commands
- Workaround: Define all commands on the root controller

**Tango Max Alarm Threshold Applied to Min Alarm:**
- Symptoms: Setting `max_alarm` on an `Int()` or `Float()` DataType silently configures the minimum alarm in Tango; no maximum alarm is set
- Files: `src/fastcs/transports/tango/util.py:26`
- Trigger: Any attribute using a numeric DataType with `max_alarm` set in the Tango transport
- Workaround: Use `min_alarm` only, or manually configure alarms outside FastCS

**Waveform PV Always Uses NTNDArray in PVA Transport:**
- Symptoms: 1D waveforms are served as `NTNDArray` (N-dimensional array, typically used for images) rather than the more appropriate `NTScalarArray` type
- Files: `src/fastcs/transports/epics/pva/types.py:71-79`
- Trigger: Any `Waveform` attribute with a 1D shape in the PVA transport
- Workaround: None until the TODO at issue #123 is resolved

**P4P Table Wrap Limitation:**
- Symptoms: `NTEnum`, `NTNDArray`, and `NTTable.wrap` do not accept extra fields; extra metadata fields (e.g., alarm, timestamp) cannot be embedded in table or enum PVs
- Files: `src/fastcs/transports/epics/pva/types.py:81-84`
- Trigger: Table or Enum PVA attributes
- Workaround: None until `https://github.com/epics-base/p4p/issues/166` is resolved

**P4P Table String Column Unsupported:**
- Symptoms: String columns in `Table` structured dtypes cause a `ValueError` when constructing the p4p type
- Files: `src/fastcs/transports/epics/pva/types.py:42-48`
- Trigger: `Table(structured_dtype=[("name", str), ...])` in PVA transport
- Workaround: Use byte arrays or other non-string types; track `https://github.com/epics-base/p4p/issues/168`

**Demo TCP Requests Concatenated:**
- Symptoms: In `TemperatureController.cancel_all`, multiple commands are sent over TCP in rapid succession; the simulated device does not handle concatenated requests properly
- Files: `src/fastcs/demo/controllers.py:92-93`
- Trigger: Calling the `cancel_all` command when multiple ramp controllers are active
- Workaround: `asyncio.sleep(0.1)` between each command (already in place as a workaround)

## Security Considerations

**No Authentication on REST and GraphQL Transports:**
- Risk: All REST and GraphQL endpoints are publicly accessible; any client can read or write any attribute or invoke any command with no authentication
- Files: `src/fastcs/transports/rest/rest.py`, `src/fastcs/transports/graphql/graphql.py`
- Current mitigation: None built in; relies entirely on network-level controls
- Recommendations: Add configurable authentication middleware (e.g., HTTP basic auth or API key) as a `RestServerOptions` field; document that these transports should only be exposed on trusted networks

**No Input Validation on REST/GraphQL Beyond Pydantic Schema:**
- Risk: Values accepted by REST/GraphQL are passed through datatype `validate()` which performs type coercion but not domain-specific validation like range checks on non-numeric types
- Files: `src/fastcs/transports/rest/rest.py`, `src/fastcs/transports/rest/util.py:34`
- Current mitigation: Pydantic model schema validation for type correctness; numeric range checks in `_Numeric.validate()`
- Recommendations: Ensure all validators raise `ValueError` on out-of-range input; confirm Pydantic ValidationErrors return 422 HTTP responses (FastAPI does this by default)

## Performance Bottlenecks

**Scan Methods Grouped by Period but Run with `asyncio.gather`:**
- Problem: All scan methods with the same period are gathered in one `asyncio.gather` call, meaning a slow method blocks others within the same period bucket
- Files: `src/fastcs/transports/controller_api.py:100-112`
- Cause: Methods sharing a period are collected into a single list and gathered synchronously; one slow coroutine delays all others in the period
- Improvement path: Wrap each scan method in an independent `asyncio.Task` instead of gathering, so individual methods can run concurrently without blocking peers

**Single Lock Serialises All IPConnection I/O:**
- Problem: `StreamConnection` uses a single `asyncio.Lock` per connection; all attribute updates sharing a connection are serialised, creating a sequential bottleneck
- Files: `src/fastcs/connections/ip_connection.py:27-46`
- Cause: Lock is acquired for both `send_command` and `send_query`, so concurrent attribute updates cannot pipeline requests
- Improvement path: Investigate request pipelining or multiplexing; consider separate locks per logical operation if the underlying protocol supports it

**`deepcopy` Called on Every Attribute at Controller Init:**
- Problem: `_bind_attrs` in `BaseController` calls `deepcopy(attr)` for every class-level `Attribute` at instantiation time
- Files: `src/fastcs/controllers/base_controller.py:115`
- Cause: Ensures attribute instances are unique per controller instance; `deepcopy` on complex objects can be slow
- Improvement path: Profile with `tests/benchmarking/test_benchmarking.py`; consider a lighter clone mechanism on `Attribute` itself (e.g., a `copy()` method)

## Fragile Areas

**`BaseController.__setattr__` Override:**
- Files: `src/fastcs/controllers/base_controller.py:149-159`
- Why fragile: Every attribute assignment on a controller instance goes through a type-dispatch in `__setattr__`; Python internals that assign class state during `__init__` (e.g., dataclass field initialisation) bypass this only if they call `super().__setattr__`. Adding new tracked types requires updating this method.
- Safe modification: Always call `super().__setattr__(name, value)` at the end of the `else` branch (which it does), but new collaborating types must be added here explicitly
- Test coverage: Covered in controller unit tests but edge cases around `__init__` ordering can be subtle

**Tango Transport Uses a Captured Event Loop Across Threads:**
- Files: `src/fastcs/transports/tango/dsr.py:34-55`
- Why fragile: `_run_threadsafe_blocking` captures the asyncio event loop at startup and uses `asyncio.run_coroutine_threadsafe` to bridge Tango's thread-based server to FastCS's async loop. If the event loop is replaced or closed, this silently stops working.
- Safe modification: Ensure `loop` is the same loop FastCS is running; do not allow the Tango transport to be re-used after the loop is closed
- Test coverage: Limited—`tests/transports/tango/test_dsr.py` exists but Tango tests are inherently harder to run without a Tango database

**`Tracer` Accesses Private Attribute Across Instance Boundary:**
- Files: `src/fastcs/tracer.py:49`
- Why fragile: `topic.__tracing_enabled` accesses a name-mangled attribute (`__tracing_enabled`) on another `Tracer` instance via `# noqa: SLF001`. This relies on Python name-mangling behaviour where `__attr` in class `Tracer` becomes `_Tracer__attr`, accessible from within the same class regardless of instance.
- Safe modification: This pattern is valid in Python but surprising; if `Tracer` is subclassed by a class that also defines `__tracing_enabled`, the mangling may diverge
- Test coverage: Not directly tested for the cross-instance access pattern

**`_GenericAlias` Usage for Type Hint Detection:**
- Files: `src/fastcs/controllers/base_controller.py:6`, `src/fastcs/controllers/base_controller.py:66`
- Why fragile: `_GenericAlias` is a private CPython implementation detail. Its behaviour (and existence) is not guaranteed across Python versions. `isinstance(hint, _GenericAlias)` was suppressed with `# type: ignore`.
- Safe modification: This detection is needed to find parameterised generics like `AttrR[int]`. Test the controller initialisation path carefully after any Python version upgrade.
- Test coverage: Covered by controller introspection tests but not explicitly for Python version compatibility

**`EpicsGUI._get_read_widget` Called with Bare `AttrR` in PVA GUI:**
- Files: `src/fastcs/transports/epics/pva/gui.py:35`
- Why fragile: `PvaEpicsGUI._get_read_widget` constructs temporary `AttrR(datatype)` instances with no `name`, `path`, or `io_ref` set, then passes them to the parent `_get_read_widget`. The parent uses `attribute.datatype` but other code paths that call `_get_read_widget` may rely on a fully initialised attribute.
- Safe modification: Verify the parent `_get_read_widget` only reads `.datatype`; avoid expanding its access to other attribute fields without updating this call site
- Test coverage: `tests/transports/epics/pva/test_pva_gui.py` covers GUI generation but may not exercise all partial-attribute paths

## Scaling Limits

**EPICS PV Name Length Hard Limit:**
- Current capacity: 60 characters (`EPICS_MAX_NAME_LENGTH`)
- Limit: Attributes or commands whose full PV name (prefix + name) exceeds 60 characters are silently disabled (`attribute.enabled = False`) and not created
- Files: `src/fastcs/transports/epics/ca/ioc.py:26-154`
- Scaling path: Deep controller hierarchies with long attribute names hit this limit; consider abbreviating path segments or surfacing a warning to the user earlier (currently uses `print()` instead of the logger)

**Tango Attribute Count Limited by Dynamic Class Construction:**
- Current capacity: Tango attribute dict is built in a single `dict` merge at device creation; large controllers will accumulate large class dicts
- Limit: No hard limit, but deeply nested controller hierarchies flatten all attributes into a single Tango device class, which may hit Tango limits or performance issues at scale
- Files: `src/fastcs/transports/tango/dsr.py:183-194`
- Scaling path: Split large controllers into multiple Tango device servers

**MBB Record Limit for Enum in EPICS CA:**
- Current capacity: 16 enum members can be represented as an MBB (multi-bit binary) EPICS record
- Limit: Enums with more than 16 members fall back to a long string record with a custom `validate` callback, which loses the enumeration type information at the EPICS layer
- Files: `src/fastcs/transports/epics/ca/util.py:92-106`
- Scaling path: Already handled via fallback; no action required, but users should be aware of the behaviour change

## Dependencies at Risk

**`pvi~=0.12.0` Pinned with Private Import:**
- Risk: `pvi._format.dls.DLSFormatter` is a private class accessed via `# type: ignore`; minor version updates to `pvi` could remove or move this without a deprecation
- Impact: GUI generation for both EPICS CA and PVA transports would break at runtime with an `ImportError`
- Files: `src/fastcs/transports/epics/gui.py:1`
- Migration plan: Request `pvi` to expose `DLSFormatter` as a public API; or write a compatibility shim that catches `ImportError` and falls back gracefully

**`tickit~=0.4.3` Pinned to Old Version Using Pydantic v1:**
- Risk: `tickit` is pinned to a specific minor version and uses `pydantic.v1` compat shim; if tickit drops the v1 shim the demo will break
- Impact: Demo/simulation (`src/fastcs/demo/`) would break with a `ModuleNotFoundError`
- Files: `src/fastcs/demo/simulation/device.py:9`, `pyproject.toml:36`
- Migration plan: Track `https://github.com/DiamondLightSource/tickit/issues/212`

**`IPython` as a Core Dependency:**
- Risk: `IPython` is listed as a required (non-optional) dependency solely for the interactive debug shell in `FastCS.serve()`
- Impact: Every FastCS deployment pulls in the full IPython stack even if the interactive shell is never used; version conflicts are more likely
- Files: `src/fastcs/control_system.py:8`, `pyproject.toml:25`
- Migration plan: Move IPython to an optional `[interactive]` extra; make `InteractiveShellEmbed` import conditional on availability

## Missing Critical Features

**No Authentication on Network Transports:**
- Problem: REST, GraphQL, and PVA transports expose all attributes and commands with no access control
- Blocks: Production deployment to any environment where the network is not fully trusted

**No Reconnection Logic in `IPConnection`:**
- Problem: `IPConnection` has no automatic reconnection; if the TCP connection drops, all subsequent operations raise `DisconnectedError` and the controller stops updating
- Blocks: Robust production usage against hardware that may disconnect and reconnect
- Files: `src/fastcs/connections/ip_connection.py`

**No Reconnection Logic in `SerialConnection`:**
- Problem: Similar to `IPConnection`—`SerialConnection` raises `NotOpenedError` after connection is lost with no automatic recovery
- Files: `src/fastcs/connections/serial_connection.py`

## Test Coverage Gaps

**Tango Transport Integration Tests Require Live Tango Database:**
- What's not tested: `TangoDSR` attribute write-back, alarm state propagation, multi-controller scenarios
- Files: `tests/transports/tango/test_dsr.py`
- Risk: Regressions in Tango transport may only be caught in full deployment
- Priority: Medium

**REST Sub-Controller Command Registration (Known Bug):**
- What's not tested: No test exercises the REST transport with sub-controller commands; the bug described above (`root_controller_api` used instead of `controller_api`) is not caught by the test suite
- Files: `src/fastcs/transports/rest/rest.py:157`, `tests/transports/rest/test_rest.py`
- Risk: Commands on sub-controllers are silently not registered
- Priority: High

**No Tests for `asyncio.get_event_loop()` Deprecation Path:**
- What's not tested: `control_system.py` and `launch.py` use `asyncio.get_event_loop()` which is deprecated; no tests exercise behavior when called without a running loop
- Files: `src/fastcs/control_system.py:39`, `src/fastcs/launch.py:162`
- Risk: Failure under Python 3.12+ in contexts without a running loop
- Priority: High

**`SerialConnection` Lacks Tests:**
- What's not tested: `SerialConnection` has no dedicated test file; relies entirely on `aioserial` mock behavior
- Files: `src/fastcs/connections/serial_connection.py`
- Risk: Serial connection edge cases (timeout, partial reads, reconnect) go untested
- Priority: Low

---

*Concerns audit: 2026-02-23*
