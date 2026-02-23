# External Integrations

**Analysis Date:** 2026-02-23

## Control System Transports

FastCS is a control-system-agnostic framework. External control systems are integrated as
pluggable transports. Each transport is an optional install extra and a `Transport` subclass.

**EPICS Channel Access (`epicsca` extra):**
- Protocol: EPICS Channel Access (CA)
- SDK/Client: `softioc>=4.5.0` (python-softioc)
- Implementation: `src/fastcs/transports/epics/ca/transport.py`, `src/fastcs/transports/epics/ca/ioc.py`
- Auth: None - network-based access control at infrastructure level
- Config: `pv_prefix` string in `EpicsIOCOptions`; passed via YAML config file at runtime

**EPICS PV Access (`epicspva` extra):**
- Protocol: EPICS PV Access (PVA)
- SDK/Client: `p4p` (Python P4P)
- Implementation: `src/fastcs/transports/epics/pva/transport.py`, `src/fastcs/transports/epics/pva/ioc.py`
- Auth: None - network-based access control at infrastructure level
- Config: `pv_prefix` string in `EpicsIOCOptions`; passed via YAML config file at runtime
- Also produces PVI (PV Interface) metadata PVs via `src/fastcs/transports/epics/pva/pvi.py`

**Tango Controls (`tango` extra):**
- Protocol: Tango Controls DSR (Device Server)
- SDK/Client: `pytango`
- Implementation: `src/fastcs/transports/tango/transport.py`, `src/fastcs/transports/tango/dsr.py`
- Auth: Tango database authentication managed externally
- Config: `dev_name`, `dsr_instance`, `debug` in `TangoDSROptions`; passed via YAML config file
- Requires an external running Tango database; device registered via `register_dev()` in `src/fastcs/transports/tango/dsr.py`

**REST HTTP (`rest` extra):**
- Protocol: HTTP REST (GET/PUT)
- SDK/Client: `fastapi[standard]`, `uvicorn[standard]>=0.12.0`
- Implementation: `src/fastcs/transports/rest/rest.py`, `src/fastcs/transports/rest/transport.py`
- Auth: None built-in; relies on infrastructure-level controls
- Config: `host` (default: `localhost`), `port` (default: `8080`), `log_level` in `RestServerOptions`
- Endpoints: GET/PUT per attribute, PUT per command; auto-generated from `ControllerAPI`

**GraphQL (`graphql` extra):**
- Protocol: GraphQL over HTTP
- SDK/Client: `strawberry-graphql`, `uvicorn[standard]>=0.12.0`
- Implementation: `src/fastcs/transports/graphql/graphql.py`, `src/fastcs/transports/graphql/transport.py`
- Auth: None built-in
- Config: `host` (default: `localhost`), `port` (default: `8080`), `log_level` in `GraphQLServerOptions`
- Schema: dynamically generated from `ControllerAPI` attributes and commands using strawberry

## Device Connections

**TCP/IP (asyncio streams):**
- Purpose: Connect to hardware devices over TCP
- SDK/Client: Python asyncio built-ins (`asyncio.open_connection`)
- Implementation: `src/fastcs/connections/ip_connection.py`
- Config: `IPConnectionSettings(ip, port)` - default `127.0.0.1:25565`
- No external library dependency

**Serial (RS-232/RS-485):**
- Purpose: Connect to hardware devices over serial port
- SDK/Client: `aioserial`
- Implementation: `src/fastcs/connections/serial_connection.py`
- Config: `SerialConnectionSettings(port, baud)` - default baud 115200

## Data Storage

**Databases:**
- None - FastCS is a stateless in-process framework; no database client or ORM is used
- Tango transport connects to an external Tango database (external infrastructure concern, not managed by FastCS)

**File Storage:**
- Local filesystem only - YAML config files read at startup via `ruamel.yaml` in `src/fastcs/launch.py`
- EPICS GUI output files (`.bob`/`.edl`) written locally via `pvi` in `src/fastcs/transports/epics/gui.py`
- EPICS docs output written locally via `src/fastcs/transports/epics/docs.py`

**Caching:**
- None

## Authentication and Identity

**Auth Provider:**
- None built-in
- All transports rely on network/infrastructure-level access control (EPICS subnet ACLs, Tango database auth, firewall rules)

## Monitoring and Observability

**Error Tracking:**
- None (no Sentry or equivalent)

**Logging:**
- Framework: `loguru` (~=0.7) - configured in `src/fastcs/logging/_logging.py`
- Console sink: colorized structured output via `prompt_toolkit.patch_stdout.StdoutProxy`
- Graylog (optional): GELF UDP handler via `pygelf`; configured at launch time with `--graylog-endpoint <host>:<port>`
- Static and environment-sourced fields can be injected into Graylog messages via `--graylog-static-fields` and `--graylog-env-fields` CLI options
- Logging is disabled at the `fastcs` namespace level unless explicitly enabled via `--log-level`

**Coverage:**
- Codecov - coverage XML uploaded in CI via `codecov/codecov-action@v5` in `.github/workflows/_test.yml`
- `codecov.yaml` excludes `src/fastcs/demo/` from coverage reporting

## CI/CD and Deployment

**Hosting:**
- PyPI - packages published on git tag push via `.github/workflows/_pypi.yml`
- GitHub Pages - documentation deployed via `.github/workflows/_docs.yml`

**CI Pipeline:**
- GitHub Actions - defined in `.github/workflows/ci.yml`
- Jobs: `lint` (pre-commit + pyright), `test` (matrix: Python 3.11/3.12/3.13 on ubuntu-latest), `docs`, `dist`, `pypi` (tag only), `release` (tag only)
- All jobs use `uv run --locked tox` as the execution wrapper
- PyPI publishing uses trusted publishing (OIDC `id-token: write`) - no stored secrets required

## EPICS GUI Generation

**pvi (~=0.12.0):**
- Purpose: Generate EPICS operator interface screens (`.bob` Phoebus, `.edl` EDM)
- SDK: `pvi` Python package (`pvi._format.dls.DLSFormatter`, `pvi.device.*`)
- Implementation: `src/fastcs/transports/epics/gui.py` (CA), `src/fastcs/transports/epics/pva/gui.py` (PVA)
- Output: local files at a configured `output_path`; format selected by `EpicsGUIFormat` enum

## Demo / Simulation

**tickit (~=0.4.3, `demo` extra):**
- Purpose: Simulate hardware devices for testing and demonstration
- Implementation: `src/fastcs/demo/simulation/device.py`, `src/fastcs/demo/controllers.py`
- Entry point: `fastcs-demo` console script defined in `pyproject.toml`

## Webhooks and Callbacks

**Incoming:**
- None - no webhook endpoints

**Outgoing:**
- None - no outgoing HTTP callbacks

## Environment Configuration

**Required at runtime:**
- YAML config file path - passed as positional argument to the `run` subcommand
- The YAML must satisfy the JSON schema derivable from the Controller's type-hinted `__init__`

**Optional CLI flags:**
- `--log-level` - One of TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
- `--graylog-endpoint` - `<host>:<port>` for GELF UDP log forwarding
- `--graylog-static-fields` - `<field>:<value>,...` static Graylog fields
- `--graylog-env-fields` - `<field>:<env_var>,...` environment-sourced Graylog fields

**Secrets location:**
- No secrets management detected; no `.env` files, no secrets directory

---

*Integration audit: 2026-02-23*
