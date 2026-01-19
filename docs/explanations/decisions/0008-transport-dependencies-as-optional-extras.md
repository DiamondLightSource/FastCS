# 8. Split Transport Dependencies into Optional Extras

Date: 2025-09-30

**Related:** [PR #221](https://github.com/DiamondLightSource/FastCS/pull/221)

## Status

Accepted

## Context

FastCS supports multiple transport protocols for exposing controller APIs: EPICS CA, EPICS PVA, Tango, REST, and GraphQL. Originally, all transport dependencies were required dependencies, meaning they were always installed regardless of which transports users actually needed.

**Original Architecture - All Dependencies Required:**

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi[standard]",  # For REST
    "numpy",
    "pydantic",
    "pvi~=0.11.0",        # For EPICS GUI generation
    "pytango",            # For Tango
    "softioc>=4.5.0",     # For EPICS CA
    "strawberry-graphql",  # For GraphQL
    "p4p",                # For EPICS PVA
    "IPython",
    "ruamel.yaml",
]
```

This meant every FastCS installation included:
- Python bindings for EPICS CA (softioc)
- Python bindings for EPICS PVA (p4p)
- Python bindings for Tango (pytango)
- Web frameworks (FastAPI, Strawberry GraphQL)
- GUI generation tools (pvi)

**Problems with Required Dependencies:**

The system needed a way to:
- Install only the dependencies for transports actually being used
- Allow minimal installations for simple use cases
- Make dependency relationships explicit and documented
- Support "install everything" for development
- Reduce installation failures for unused transports

## Decision

We split transport dependencies into optional extras in `pyproject.toml`, allowing users to install only what they need.

### New Architecture

**Core Dependencies (Minimal):**

```toml
[project]
dependencies = [
    "pydantic",      # Core data validation
    "numpy",         # Numeric types
    "ruamel.yaml",   # YAML config parsing
    "IPython",       # Interactive shell
]
```

**Transport-Specific Extras:**

```toml
[project.optional-dependencies]
# Individual transports
epicsca = ["pvi~=0.11.0", "softioc>=4.5.0"]
epicspva = ["p4p", "pvi~=0.11.0"]
tango = ["pytango"]
graphql = ["strawberry-graphql", "uvicorn[standard]>=0.12.0"]
rest = ["fastapi[standard]", "numpy", "uvicorn[standard]>=0.12.0"]

# Convenience groups
epics = ["fastcs[epicsca]", "fastcs[epicspva]"]
all = ["fastcs[epics]", "fastcs[tango]", "fastcs[graphql]", "fastcs[rest]"]

# Development and demos
demo = ["tickit~=0.4.3"]
dev = [
    "fastcs[all]",  # Dev installs everything
    "fastcs[demo]",
    # ... test tools, docs tools, etc.
]
```

### Installation Examples

**1. Minimal Installation (Core only):**
```bash
pip install fastcs
# Only: pydantic, numpy, ruamel.yaml, IPython
```

**2. Single Transport:**
```bash
pip install fastcs[epicspva]  # EPICS PVA only
pip install fastcs[rest]      # REST API only
pip install fastcs[tango]     # Tango only
```

**3. Multiple Transports:**
```bash
pip install fastcs[epics,rest]  # EPICS CA + PVA + REST
```

**4. All Transports:**
```bash
pip install fastcs[all]  # Everything
```

**5. Development:**
```bash
pip install fastcs[dev]  # All transports + dev tools
```

### Key Benefits

1. **Clearer Documentation:**
   - Extras make dependencies explicit: `pip install fastcs[epicspva]`
   - Users understand what each transport needs
   - Self-documenting installation commands

2. **Development Convenience:**
   - `fastcs[dev]` installs everything for development
   - `fastcs[all]` installs all transports without dev tools
   - Clear separation of concerns

## Consequences

### Technical Changes

- Updated `pyproject.toml`:
  - Moved transport dependencies from `dependencies` to `optional-dependencies`
  - Created extras: `epicsca`, `epicspva`, `tango`, `graphql`, `rest`
  - Created convenience groups: `epics`, `all`, `dev`, `demo`
  - Kept only core dependencies in main `dependencies` list

### Migration Impact

For existing users:

**Before:**
```bash
pip install fastcs  # Gets everything
```

**After:**
```bash
# Option 1: Get everything (same as before)
pip install fastcs[all]

# Option 2: Get only what you need
pip install fastcs[epicspva]
pip install fastcs[rest,epics]
```

For developers:

**Before:**
```bash
pip install -e .[dev]  # Got everything
```

**After:**
```bash
pip install -e .[dev]  # Still gets everything (includes [all])
```

### Architectural Impact

This decision established a flexible dependency model:

```
fastcs (core)
    ├── fastcs[epicsca] → softioc, pvi
    ├── fastcs[epicspva] → p4p, pvi
    ├── fastcs[tango] → pytango
    ├── fastcs[graphql] → strawberry-graphql, uvicorn
    ├── fastcs[rest] → fastapi, uvicorn
    ├── fastcs[epics] → [epicsca] + [epicspva]
    ├── fastcs[all] → all transports
    └── fastcs[dev] → [all] + dev tools
```

The split into optional extras aligned with FastCS's philosophy of supporting multiple transports while keeping the core lightweight. Users can now install exactly what they need, reducing friction and improving deployment efficiency, while developers can still easily install everything with `fastcs[dev]`.
