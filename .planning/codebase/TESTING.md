# Testing Patterns

**Analysis Date:** 2026-02-23

## Test Framework

**Runner:**
- pytest — config in `pyproject.toml` `[tool.pytest.ini_options]`
- Run via `tox -e tests` (with coverage) or `pytest` directly

**Key Plugins:**
- `pytest-asyncio` — async test support
- `pytest-mock` — mocking via `mocker` fixture
- `pytest-benchmark` — performance benchmarking
- `pytest-forked` — isolated subprocess test execution
- `pytest-cov` — coverage reporting
- `pytest-markdown-docs` — doctest in markdown files
- `pytest-timeout` — per-test timeout (default: 5 seconds)

**Run Commands:**
```bash
pytest                                          # Run all tests (unit + doctests)
tox -e tests                                    # Run with coverage (CI)
pytest --cov=fastcs --cov-report term           # Run with terminal coverage
pytest tests/test_attributes.py                 # Run single file
pytest -k test_attr_r                           # Run matching tests
```

## Test File Organization

**Location:**
- All tests in `tests/` directory, separate from `src/`
- Transport-specific tests in subdirectories mirroring transport structure:
  ```
  tests/
  ├── conftest.py                          # Shared fixtures
  ├── assertable_controller.py            # Test controller helpers
  ├── example_softioc.py                  # EPICS CA IOC runner for subprocess tests
  ├── example_p4p_ioc.py                  # EPICS PVA IOC runner for subprocess tests
  ├── util.py                              # Shared test utilities (e.g., ColourEnum)
  ├── test_attributes.py
  ├── test_controllers.py
  ├── test_control_system.py
  ├── test_datatypes.py
  ├── test_launch.py
  ├── test_methods.py
  ├── test_util.py
  ├── test_docs_snippets.py
  └── transports/
      ├── epics/
      │   ├── ca/
      │   │   ├── test_ca_util.py
      │   │   ├── test_softioc.py
      │   │   ├── test_softioc_system.py   # Full subprocess system test
      │   │   ├── test_gui.py
      │   │   └── test_initial_value.py
      │   ├── pva/
      │   │   ├── test_p4p.py
      │   │   └── test_pva_gui.py
      │   └── test_epics_util.py
      ├── rest/
      │   └── test_rest.py
      ├── graphQL/
      │   └── test_graphql.py
      └── tango/
          └── test_dsr.py
  ```

**Naming:**
- Test files: `test_<module_name>.py`
- Test functions: `test_<what_is_being_tested>` (e.g., `test_attr_r`, `test_controller_nesting`)
- Test classes group related tests: `class TestRestServer:`, `class TestGraphQLServer:`

**Doctests:**
- `--doctest-modules` runs doctests in all `src/` docstrings
- `--doctest-glob="*.md"` runs doctests embedded in markdown docs
- `--ignore-glob docs/snippets/*py` excludes standalone snippet files from doctest collection
- Test paths: `docs src tests` (all three scanned)

## Test Structure

**Simple Unit Tests:**
```python
def test_attr_r():
    attr = AttrR(String(), group="test group")

    with pytest.raises(RuntimeError):
        _ = attr.io_ref

    assert not attr.has_io_ref()
    assert isinstance(attr.datatype, String)
    assert attr.dtype == str
```

**Async Tests:**
```python
@pytest.mark.asyncio
async def test_attr_update(mocker: MockerFixture):
    attr = AttrRW(Int())

    await attr.update(42)
    assert attr.get() == 42

    with pytest.raises(ValueError, match="Failed to cast"):
        await attr.update("not_an_int")  # type: ignore
```

**Parametrized Tests:**
```python
@pytest.mark.parametrize(
    ["datatype", "init_args", "value"],
    [
        (Int, {"min": 1}, 0),
        (Float, {"max": -1}, 0.0),
        (Enum, {"enum_cls": int}, 0),
    ],
)
def test_validate(datatype, init_args, value):
    with pytest.raises(ValueError):
        datatype(**init_args).validate(value)
```

**Class-Grouped Tests:**
```python
class TestRestServer:
    @pytest.fixture(scope="class")
    def test_client(self, rest_controller_api):
        with create_test_client(rest_controller_api) as test_client:
            yield test_client

    def test_read_write_int(
        self, rest_controller_api: AssertableControllerAPI, test_client: TestClient
    ):
        with rest_controller_api.assert_read_here(["read_write_int"]):
            response = test_client.get("/read-write-int")
        assert response.status_code == 200
        assert response.json()["value"] == 0
```

## Mocking

**Framework:** `pytest-mock` (`MockerFixture`)

**Patterns:**
```python
# Patch a module-level name
mocker.patch("fastcs.transports.epics.ca.ioc.builder")

# Patch and get return value
make_record = mocker.patch("fastcs.transports.epics.ca.ioc._make_record")
record = make_record.return_value

# Spy on an existing method (real implementation still runs)
wait_mock = mocker.spy(asyncio, "wait_for")
assert wait_mock.call_count == 2

# Async mock
sync_setpoint_mock = mocker.AsyncMock()
attr.add_sync_setpoint_callback(sync_setpoint_mock)
sync_setpoint_mock.assert_called_once_with(200)

# MagicMock for complex objects
attribute = mocker.MagicMock()
attribute.put = mocker.AsyncMock()

# PropertyMock for properties
mocker.patch(
    "fastcs.transports.Transport.context",
    new_callable=mocker.PropertyMock,
    return_value={"controller": "test"},
)
```

**`class_mocker` for class-scoped fixtures:**
```python
@pytest.fixture(scope="class")
def rest_controller_api(class_mocker: MockerFixture):
    return AssertableControllerAPI(RestController(), class_mocker)
```

**What to Mock:**
- External EPICS `builder` calls (softioc) — avoid process-level side effects in unit tests
- FastCS internal functions when testing integration at a higher level
- Async methods on attributes (`put`, `add_sync_setpoint_callback`) when testing transport wiring

**What NOT to Mock:**
- Core `fastcs` domain logic in unit tests (attributes, datatypes, controllers) — test directly
- `AssertableControllerAPI` provides real `Controller` behaviour with spy wrappers

## Fixtures and Factories

**`conftest.py` Shared Fixtures** (`tests/conftest.py`):
```python
@pytest.fixture(scope="function", autouse=True)
def clear_softioc_records():
    """Auto-clears softioc builder records before each test."""
    builder.ClearRecords()

@pytest.fixture
def controller():
    return BackendTestController()

@pytest.fixture
def controller_api(controller):
    return build_controller_api(controller)

@pytest.fixture
def data() -> Path:
    """Returns Path to tests/data/ for reference files."""
    return DATA_PATH

@pytest.fixture
def event_loop():
    """Fresh asyncio event loop per test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
```

**Subprocess Fixtures for System Tests:**
```python
@pytest.fixture(scope="module")
def softioc_subprocess():
    """Starts a real EPICS CA IOC in a subprocess; yields (pv_prefix, stdout_queue)."""
    multiprocessing.set_start_method("spawn", force=True)
    yield from run_ioc_as_subprocess(_run_softioc, multiprocessing.get_context())

@pytest.fixture(scope="module")
def p4p_subprocess():
    """Starts a real EPICS PVA IOC in a subprocess; yields (pv_prefix, stdout_queue)."""
    multiprocessing.set_start_method("forkserver", force=True)
    yield from run_ioc_as_subprocess(_run_p4p_ioc, multiprocessing.get_context())
```

**`AssertableControllerAPI`** (`tests/assertable_controller.py`):
- Wraps a real `Controller` with spy-backed assertion helpers
- Used by transport tests to verify attribute IO is wired correctly:
  ```python
  with controller_api.assert_read_here(["read_write_int"]):
      response = test_client.get("/read-write-int")

  with controller_api.assert_write_here(["SubController01", "read_int"]):
      test_client.put("/SubController01/read-int", json={"value": 5})

  with controller_api.assert_execute_here(["go"]):
      test_client.put("/go")
  ```
- Context manager asserts the named attribute method was called exactly once

**Test Controller Hierarchy:**
- `MyTestController` — base test controller with sub-controllers, scan, command (`tests/assertable_controller.py`)
- Transport test controllers extend `MyTestController` adding datatype-specific attributes:
  ```python
  class RestController(MyTestController):
      read_int = AttrR(Int())
      read_write_int = AttrRW(Int())
      enum = AttrRW(Enum(...))
      one_d_waveform = AttrRW(Waveform(np.int32, (10,)))
  ```

**Reference Data:**
- `tests/data/` contains reference JSON/YAML files (e.g., `schema.json`, `config.yaml`)
- Loaded via the `data` fixture: `data / "schema.json"`
- Regenerated by setting env var: `FASTCS_REGENERATE_OUTPUT=1`

## Coverage

**Requirements:** No minimum threshold enforced in CI, but coverage is always collected

**Configuration** (`pyproject.toml` `[tool.coverage]`):
```toml
[tool.coverage.run]
data_file = "/tmp/fastcs.coverage"
concurrency = ["thread", "multiprocessing"]
omit = ["tests/*", "src/fastcs/demo/*"]

[tool.coverage.paths]
source = ["src", "**/site-packages/"]
```

**View Coverage:**
```bash
tox -e tests                                    # Runs with --cov-report term and xml:cov.xml
pytest --cov=fastcs --cov-report term           # Terminal report
pytest --cov=fastcs --cov-report html           # HTML report
```

## Test Types

**Unit Tests:**
- Scope: individual classes and functions in isolation
- Files: `test_attributes.py`, `test_controllers.py`, `test_datatypes.py`, `test_methods.py`, `test_util.py`
- Use direct instantiation; mock only external/side-effectful dependencies
- Async tests decorated with `@pytest.mark.asyncio`

**Transport Integration Tests:**
- Scope: full transport layer against a mock or real controller API
- Files: `tests/transports/*/test_*.py`
- Use `AssertableControllerAPI` + `fastapi.testclient.TestClient` for REST/GraphQL
- Use `mocker.patch` on EPICS builder for CA/PVA unit-level transport tests

**System Tests (subprocess-based):**
- Scope: full end-to-end against a live IOC process
- Files: `tests/transports/epics/ca/test_softioc_system.py`, `tests/transports/epics/pva/test_p4p.py`
- Use `softioc_subprocess` / `p4p_subprocess` fixtures (module-scoped subprocess)
- Tests are slow; kept module-scoped to amortise startup cost

**Forked Tests:**
- `@pytest.mark.forked` for tests that require a clean process (e.g., EPICS CA initial values in `test_initial_value.py`)
- Requires `pytest-forked`

**Benchmark Tests:**
- Files: `tests/benchmarking/test_benchmarking.py`
- All guarded by `@pytest.mark.skipif(not FASTCS_BENCHMARKING, ...)` — opt-in via `FASTCS_BENCHMARKING=true`
- Use `pytest-benchmark`'s `benchmark` fixture
- Sorted by `mean`, columns: `mean, min, max, outliers, ops, rounds`

**Doctest:**
- All `src/` docstrings tested via `--doctest-modules`
- All `docs/*.md` code blocks tested via `--doctest-glob="*.md"`

## Common Patterns

**Testing Exception Messages:**
```python
with pytest.raises(ValueError, match="Failed to cast"):
    await attr.update("not_an_int")

with pytest.raises(RuntimeError, match="does not match defined datatype"):
    controller.add_attribute("read_write_int", AttrRW(Float()))
```

**Testing Async with Timing:**
```python
@pytest.mark.asyncio
async def test_scan_tasks(controller):
    loop = asyncio.get_event_loop()
    fastcs = FastCS(controller, [], loop)

    asyncio.create_task(fastcs.serve(interactive=False))
    await asyncio.sleep(0.1)   # allow scan to execute

    for _ in range(3):
        count = controller.count
        await asyncio.sleep(0.1)
        assert controller.count > count
```

**Testing CLI with typer:**
```python
runner = CliRunner()

def test_version():
    app = _launch(SingleArg, version="0.0.1")
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "FastCS" in result.stdout
```

**Spy on Real Methods:**
```python
@pytest.mark.asyncio
async def test_wait_for_predicate(mocker: MockerFixture):
    wait_mock = mocker.spy(asyncio, "wait_for")
    with pytest.raises(TimeoutError):
        await attr.wait_for_predicate(predicate, timeout=0.2)
    await attr.wait_for_predicate(predicate, timeout=1)
    assert wait_mock.call_count == 2
```

**Testing Private Internals:**
- `SLF001` suppressed for `tests/**/*` — direct access to `_private` members permitted in tests
- Example: `rest_transport._server._app`, `fastcs._scan_tasks`, `c._connect_attribute_ios()`

**Global Test Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
addopts = "--tb=native -vv --doctest-modules --doctest-glob='*.md' ..."
filterwarnings = "error"   # All warnings become errors
timeout = 5                # 5-second default timeout per test
testpaths = "docs src tests"
```

---

*Testing analysis: 2026-02-23*
