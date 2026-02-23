# Technology Stack

**Analysis Date:** 2026-02-23

## Languages

**Primary:**
- Python 3.11+ - All source code in `src/fastcs/` and `tests/`

**Secondary:**
- reStructuredText - Sphinx API docs in `docs/_api.rst`
- YAML - Runtime configuration loaded from config files passed to `launch()`
- Markdown - Documentation in `docs/`

## Runtime

**Environment:**
- Python 3.11, 3.12, 3.13 (all three supported; see CI matrix in `.github/workflows/ci.yml`)
- Minimum required: Python 3.11 (`requires-python = ">=3.11"` in `pyproject.toml`)
- asyncio event loop is the execution model - `asyncio.get_event_loop()` used in `src/fastcs/control_system.py`

**Package Manager:**
- uv - Used for all CI operations (`uv run --locked tox`) in `.github/workflows/_tox.yml`
- Lockfile: `uv.lock` present and committed

## Frameworks

**Core:**
- FastAPI (with `standard` extras) - REST HTTP server in `src/fastcs/transports/rest/rest.py`
- Pydantic - Schema generation, config model validation throughout `src/fastcs/launch.py`
- Typer - CLI entry point built in `src/fastcs/launch.py`
- ruamel.yaml - YAML config file loading in `src/fastcs/launch.py`
- IPython - Interactive embedded shell in `src/fastcs/control_system.py`

**Transport / Control System:**
- softioc (>=4.5.0, optional `epicsca`) - EPICS Channel Access IOC in `src/fastcs/transports/epics/ca/ioc.py`
- p4p (optional `epicspva`) - EPICS PV Access IOC in `src/fastcs/transports/epics/pva/ioc.py`
- pvi (~=0.12.0, optional `epics`) - EPICS GUI generation (`.bob`/`.edl`) in `src/fastcs/transports/epics/gui.py` and `src/fastcs/transports/epics/pva/gui.py`
- pytango (optional `tango`) - Tango Controls Device Server in `src/fastcs/transports/tango/dsr.py`
- strawberry-graphql (optional `graphql`) - GraphQL schema/server in `src/fastcs/transports/graphql/graphql.py`
- uvicorn (optional `rest`/`graphql`) - ASGI server for REST and GraphQL transports

**Connections:**
- aioserial - Async serial communication in `src/fastcs/connections/serial_connection.py`
- asyncio built-in StreamReader/StreamWriter - TCP/IP connection in `src/fastcs/connections/ip_connection.py`

**Logging:**
- loguru (~=0.7) - Structured logging throughout `src/fastcs/logging/_logging.py`
- pygelf - GELF/UDP handler for Graylog in `src/fastcs/logging/_logging.py`
- prompt_toolkit - stdout proxy for colorized log output

**Demo/Simulation:**
- tickit (~=0.4.3, optional `demo`) - Device simulation backend in `src/fastcs/demo/`
- numpy - Array/waveform data types throughout `src/fastcs/datatypes/`

**Testing:**
- pytest - Test runner configured in `pyproject.toml`
- pytest-asyncio - Async test support
- pytest-cov - Coverage reporting (uploads to Codecov)
- pytest-mock - Mocking support
- pytest-benchmark - Performance benchmarking
- pytest-forked - Isolated test process forking
- pytest-markdown-docs - Doctests in Markdown files
- pytest-timeout - Test timeout enforcement (5s default in `pyproject.toml`)
- aioca - EPICS CA client used in tests
- httpx - HTTP client used in integration tests

**Build/Dev:**
- setuptools (>=64) - Build backend
- setuptools_scm (>=8) - Version from git tags, writes `src/fastcs/_version.py`
- tox-uv - tox environment manager using uv
- ruff - Linting and import sorting (line-length=88, rules: B, C4, E, F, N, W, I, UP, SLF)
- pyright - Static type checking in `standard` mode
- pre-commit - Git hook enforcement
- sphinx + pydata-sphinx-theme - Documentation build
- sphinx-autobuild, sphinx-copybutton, sphinx-togglebutton, sphinx-design - Docs extras
- myst-parser - Markdown in Sphinx docs
- copier - Template-based project scaffolding

## Key Dependencies

**Critical:**
- `fastapi[standard]` - Core REST transport; used in `src/fastcs/transports/rest/rest.py`
- `pydantic` - Config validation and schema export; used in `src/fastcs/launch.py`
- `loguru~=0.7` - All internal logging; used via `src/fastcs/logging/__init__.py`
- `numpy` - Waveform/array datatypes in `src/fastcs/datatypes/waveform.py`
- `ruamel.yaml` - Runtime config parsing in `src/fastcs/launch.py`
- `aioserial` - Serial device connections in `src/fastcs/connections/serial_connection.py`
- `stdio-socket` - Standard IO socket connection support
- `pygelf` - Graylog UDP log forwarding in `src/fastcs/logging/_logging.py`
- `IPython` - Interactive diagnostic shell embedded in `src/fastcs/control_system.py`

**Infrastructure (optional extras):**
- `softioc>=4.5.0` (`epicsca`) - EPICS CA IOC; `src/fastcs/transports/epics/ca/`
- `p4p` (`epicspva`) - EPICS PVA IOC; `src/fastcs/transports/epics/pva/`
- `pvi~=0.12.0` (`epics`) - PV Interface / GUI generation; `src/fastcs/transports/epics/gui.py`
- `pytango` (`tango`) - Tango Controls DSR; `src/fastcs/transports/tango/`
- `strawberry-graphql` + `uvicorn[standard]>=0.12.0` (`graphql`) - GraphQL server; `src/fastcs/transports/graphql/`
- `tickit~=0.4.3` (`demo`) - Simulation backend; `src/fastcs/demo/`

## Configuration

**Environment:**
- No `.env` file; configuration is passed via a YAML file at runtime
- YAML file is validated against a Pydantic model derived from the Controller's `__init__` type hints
- The YAML schema can be generated via the `schema` subcommand of any launched controller
- Graylog logging configured via CLI flags: `--graylog-endpoint`, `--graylog-static-fields`, `--graylog-env-fields`
- Log level set via `--log-level` CLI option (default: INFO)

**Build:**
- `pyproject.toml` - All project metadata, dependency groups, tool config
- tox environments: `pre-commit`, `type-checking`, `tests`, `docs`, `docs-autobuild`
- Version: dynamically set from git tags via `setuptools_scm`, written to `src/fastcs/_version.py`
- Coverage config in `pyproject.toml` under `[tool.coverage]`; data file at `/tmp/fastcs.coverage`

## Platform Requirements

**Development:**
- Python >=3.11
- uv package manager
- Linux (CI runs `ubuntu-latest`; Windows noted as possible future matrix target)
- EPICS CA transport requires softioc which has system-level EPICS dependencies
- Tango transport requires pytango and a running Tango database

**Production:**
- Python >=3.11
- Deployed as a Python package; released to PyPI via GitHub Actions on tag push (`.github/workflows/_pypi.yml`)
- Uses PyPA trusted publishing (OIDC) - no stored PyPI token required
- No container/Docker configuration detected in repository

---

*Stack analysis: 2026-02-23*
