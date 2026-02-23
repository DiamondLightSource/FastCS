# Coding Conventions

**Analysis Date:** 2026-02-23

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `attribute_io.py`, `base_controller.py`)
- Private/internal modules: prefix with underscore (e.g., `_numeric.py`, `_util.py`, `_logging.py`)
- Test files: `test_<module>.py` (e.g., `test_attributes.py`, `test_controllers.py`)

**Classes:**
- `PascalCase` throughout (e.g., `Controller`, `AttrRW`, `AttributeIO`, `DataType`, `BaseController`)
- Abstract base classes named clearly: `BaseController`, `DataType`, `Attribute`
- Concrete implementations drop the abstract prefix: `Controller`, `Float`, `AttrR`
- Generic type aliases use `_T` suffix (e.g., `DType_T`, `AttributeIORefT`, `Controller_T`)
- Type aliases use descriptive `PascalCase` (e.g., `AttributeAccessMode`, `MethodCallback`, `AnyAttributeIO`)
- Callback type aliases describe their role: `AttrIOUpdateCallback`, `AttrOnUpdateCallback`, `CommandCallback`

**Functions and Methods:**
- `snake_case` for all functions and methods
- Private methods prefixed with `_` (e.g., `_bind_attrs`, `_validate_io`, `_configure_logger`)
- Double underscore for truly private instance attributes (e.g., `self.__attributes`, `self.__scan_methods`)
- Async methods use descriptive verbs: `update`, `send`, `connect`, `disconnect`, `initialise`
- Hook methods use lifecycle names: `initialise`, `post_initialise`, `connect`, `disconnect`

**Variables:**
- `snake_case` for all local variables and instance attributes
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `DEVICE`, `PV_PREFIX`, `EPICS_MAX_NAME_LENGTH`)
- Sentinel values uppercase: `ONCE = float("inf")` in `src/fastcs/util.py`
- Private instance attributes: `_name` prefix (e.g., `self._value`, `self._datatype`, `self._path`)
- Truly private class attributes: `__name` prefix (e.g., `self.__attributes`, `self.__tracing_enabled`)

**TypeVars:**
- `TypeVar` names use `_T` suffix: `DType_T`, `Controller_T`, `NumberT`, `AttributeIORefT`
- Bound to meaningful base types (e.g., `DType_T = TypeVar("DType_T", bound=DType)`)

## Code Style

**Formatting:**
- Tool: `ruff format` (enforced via pre-commit hook and `tox pre-commit` env)
- Line length: 88 characters (configured in `pyproject.toml` `[tool.ruff]`)
- End-of-file newline enforced by pre-commit `end-of-file-fixer`

**Linting:**
- Tool: `ruff check` (via pre-commit and tox)
- Config: `pyproject.toml` `[tool.ruff]`
- Enabled rule sets:
  - `B` — flake8-bugbear
  - `C4` — flake8-comprehensions
  - `E` — pycodestyle errors
  - `F` — pyflakes
  - `N` — pep8-naming
  - `W` — pycodestyle warnings
  - `I` — isort
  - `UP` — pyupgrade
  - `SLF` — private member access
- `SLF001` (private member access) suppressed in `tests/**/*` only
- Inline `# noqa: SLF001` used when private access is intentional in non-test code (e.g., `src/fastcs/controllers/base_controller.py`)

**Type Checking:**
- Tool: `pyright` in `standard` mode
- Config: `pyproject.toml` `[tool.pyright]`
- Run against both `src` and `tests` directories
- `reportMissingImports = false` to handle optional dependencies without stubs

**Pre-commit:**
- Config: `.pre-commit-config.yaml`
- Hooks: `check-added-large-files`, `check-yaml`, `check-merge-conflict`, `end-of-file-fixer`, `ruff` (lint+fix), `ruff-format`, `uv-sync`, `gitleaks` (secret scanning)

## Import Organization

**Order (enforced by ruff `I` isort rules):**
1. Standard library (`asyncio`, `collections`, `dataclasses`, `typing`, etc.)
2. Third-party (`numpy`, `pydantic`, `loguru`, `pytest`, etc.)
3. First-party `fastcs.*` absolute imports
4. Relative imports within packages (`.attr_r`, `.attribute`, etc.)

**Public API Re-exports:**
- `__init__.py` files re-export with explicit `as` alias to mark as intentionally public:
  ```python
  # src/fastcs/attributes/__init__.py
  from .attr_r import AttrR as AttrR
  from .attr_rw import AttrRW as AttrRW
  from .attribute_io import AttributeIO as AttributeIO
  ```
- Top-level `src/fastcs/__init__.py` exposes minimal public API:
  ```python
  from .control_system import FastCS as FastCS
  from .launch import launch as launch
  from .util import ONCE as ONCE
  ```

**Circular Import Avoidance:**
- `TYPE_CHECKING` guard used for forward references:
  ```python
  if TYPE_CHECKING:
      from fastcs.controllers import BaseController
  ```
- `from __future__ import annotations` used at module top where needed (e.g., `src/fastcs/attributes/attr_r.py`)

## Error Handling

**Exception Types:**
- `ValueError` — invalid data, configuration, or argument values
- `RuntimeError` — unexpected program state (duplicate registration, missing callback)
- `TypeError` — incorrect function signatures caught by framework validation
- `NotImplementedError` — abstract-like methods that subclasses must override
- `TimeoutError` — async wait operations that exceed configured timeout
- Custom: `FastCSError` (base), `LaunchError` — defined in `src/fastcs/exceptions.py`

**Raise Patterns:**
- Error messages include object identity and full context using f-strings:
  ```python
  raise ValueError(
      f"Cannot add attribute {attr}. "
      f"Controller {self} has existing attribute {name}: {self.__attributes[name]}"
  )
  ```
- Chain with `from e` when catching and re-raising with added context:
  ```python
  except (ValueError, TypeError) as e:
      raise ValueError(f"Failed to cast {value} to type {self.dtype}") from e
  ```
- Suppress context with `from None` when new exception is self-explanatory:
  ```python
  raise TimeoutError(
      f"Timeout waiting {timeout}s for {self.full_name} predicate {predicate}"
  ) from None
  ```

**Async Error Handling:**
- Exceptions in on-update callbacks are logged before re-raising:
  ```python
  except Exception as e:
      logger.opt(exception=e).error(
          "On update callbacks failed",
          attribute=self,
          value=repr(self._value),
      )
      raise
  ```
- Command failures logged with `logger.exception("Command failed", fn=self._fn)` before re-raise
- Scan task exceptions propagated to the event loop exception handler

## Logging

**Framework:** `loguru` via `src/fastcs/logging/__init__.py`

**Singleton Logger:**
- Single `logger` instance in `fastcs.logging`, bound with `logger_name="fastcs"`
- Disabled for `fastcs` namespace by default until `configure_logging` is called

**Module Logger Pattern:**
```python
from fastcs.logging import bind_logger

logger = bind_logger(logger_name=__name__)
```

**Log Statement Style:**
- Short message as first arg, structured key=value extras as kwargs:
  ```python
  logger.info("PV put: {pv} = {value}", pv=pv, value=value)
  logger.debug("Validated hinted attribute", name=name, controller=self, attribute=attr)
  ```
- Keys prefixed with `_` appear in message format only, not as structured extra fields

**Trace Logging:**
- `Tracer` mixin class (`src/fastcs/tracer.py`) provides per-instance verbose logging
- Inherited by `Attribute`, `Method`, `BaseController`
- Use `self.log_event("Event description", key=value, ...)` from `Tracer` subclasses
- Do NOT use `logger.trace()` directly — use `Tracer` instead
- Disabled by default; users enable per-instance: `obj.enable_tracing()`
- Supports filters: `obj.add_tracing_filter("query", "V?")`

**Log Levels** (from `src/fastcs/logging/_logging.py`):
- `LogLevel` `StrEnum`: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- Default level: `INFO`

## Comments

**When to Comment:**
- Non-obvious logic: explain intent inline
- `# type: ignore` with specific rule where pyright cannot infer correctly
- `# noqa: SLF001` where private member access in non-test code is intentional
- TODO comments for incomplete items (e.g., `# TODO cover Waveform and Table cases` in `tests/transports/epics/ca/test_ca_util.py`)
- Commented-out code kept only with explicit explanation (e.g., `# store a schema to use for debugging` in `tests/test_launch.py`)

**Docstrings:**
- Class and public method docstrings required — they are run as doctests via `--doctest-modules`
- Method docstrings use Google/NumPy-style sections:
  ```python
  def validate(self, value: Any) -> DType_T:
      """Validate a value against the datatype.

      Args:
          value: The value to validate

      Returns:
          The validated value

      Raises:
          ValueError: If the value cannot be coerced

      """
  ```
- One-line docstrings for simple properties and trivial methods
- Module-level docstrings on public `__init__.py` explain the public API

## Function and Method Design

**Async:**
- All IO, lifecycle, and callback methods must be `async def`
- Framework enforces this: `Method.__init__` raises `TypeError` if function is not a coroutine
- Sync methods used only for pure computation, property access, and configuration

**Parameters:**
- `| None` union with `None` default for optional parameters (not `Optional[X]`):
  ```python
  def __init__(self, group: str | None = None, description: str | None = None) -> None:
  ```
- Keyword-only arguments enforced with `*` separator for optional settings
- Full type hints on all parameters and return types required

**Return Values:**
- Methods that mutate state return `None` (implicit)
- Abstract methods raise `NotImplementedError` rather than returning a stub value
- `__repr__` uses `None` for absent optional fields: `f"ClassName(key={value or None})"`

## Module Design

**Exports:**
- All public symbols re-exported with `as` alias in `__init__.py`
- Internal files use `_` prefix and are not re-exported
- `src/fastcs/__init__.py` is the minimal public surface — keep additions deliberate

**Dataclasses:**
- `@dataclass(frozen=True)` for immutable value objects: all `DataType` subclasses (`src/fastcs/datatypes/`), `AttributeIORef` subclasses
- `@dataclass` (mutable) for simple data holders in tests and config

**Abstract Patterns:**
- `ABC` + `@abstractmethod` for explicit abstract interfaces: `Attribute`, `DataType` (`src/fastcs/attributes/attribute.py`, `src/fastcs/datatypes/datatype.py`)
- Raise `NotImplementedError` in semi-abstract base methods: `AttributeIO.update`, `AttributeIO.send` (`src/fastcs/attributes/attribute_io.py`)
- Runtime validation in `__init__` for protocol enforcement: `Method._validate` checks coroutine and return type

---

*Convention analysis: 2026-02-23*
