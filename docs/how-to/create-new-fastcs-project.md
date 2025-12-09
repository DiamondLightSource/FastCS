# Creating a New FastCS Project

## Overview

This guide shows you how to set up a new FastCS project using the Diamond Light Source Python copier template. The template provides a complete, production-ready project structure with modern Python tooling and best practices built-in.

## Prerequisites

Before starting, ensure you have:

- Python 3.11 or later installed
- Basic understanding of Python development
- (Optional) VS Code for using the devcontainer

## Install UV

First, install `uv` (a fast Python package installer) following the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

**For Diamond Light Source users**, `uv` is available as a module:

```bash
module load uv
```

## Generate Project from Template

```bash
uvx copier copy https://github.com/DiamondLightSource/python-copier-template my-device-ioc
cd my-device-ioc
```

You'll be prompted for project details. Read the [python-copier-template documentation](https://diamondlightsource.github.io/python-copier-template/main/index.html) to understand each option. Answer the prompts to name and customize your project.

The template creates a complete project structure including:
- Standard Python package layout
- Pre-configured testing with pytest
- Linting and formatting tools (ruff, mypy)
- GitHub Actions CI/CD workflows
- Documentation structure with Sphinx
- VS Code devcontainer configuration
- pyproject.toml with modern build system

## Recommended: Use the Devcontainer

The template includes a VS Code devcontainer with all development tools pre-installed. This is the recommended way to develop FastCS projects as it ensures consistency across different environments.

**To use the devcontainer:**

1. Open the project in VS Code:
   ```bash
   code my-device-ioc
   ```

2. When prompted, click "Reopen in Container" (or press `Ctrl+Shift+P` and select "Dev Containers: Reopen in Container")

3. VS Code will build the container with all dependencies installed

4. You now have a complete development environment with:
   - Python 3.11+
   - All development tools (pytest, ruff, mypy)
   - EPICS tools (caget, caput, pvget, pvput)
   - Pre-configured Git and editor settings

## Add FastCS Dependencies

Use `uv` to add FastCS to your project. The extras you need depend on which transports you want to use:

### For EPICS IOCs (CA and PVA)

```bash
uv add 'fastcs[ca,pva]'
```

This includes:
- `ca` extra for Channel Access (pythonSoftIOC)
- `pva` extra for PV Access (p4p)

### For Other Transports

```bash
# Tango
uv add 'fastcs[tango]'

# GraphQL
uv add 'fastcs[graphql]'

# Multiple transports
uv add 'fastcs[ca,pva,tango]'
```

### Manual Installation

Alternatively, edit `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastcs[ca,pva]",
]
```

Then run:
```bash
uv sync
```

## Verify Installation

```bash
uv run python -c "from fastcs import __version__; print(f'FastCS version: {__version__}')"
```

You should see the FastCS version number printed.

## Project Structure

After setup, your project will have this structure:

```
my-device-ioc/
├── .devcontainer/          # VS Code devcontainer configuration
├── .github/
│   └── workflows/          # CI/CD workflows
├── docs/                   # Sphinx documentation
├── src/
│   └── my_device_ioc/      # Your Python package
│       └── __init__.py
├── tests/                  # pytest tests
├── pyproject.toml          # Project metadata and dependencies
├── README.md
└── uv.lock                 # Locked dependency versions
```

## Next Steps

Now that you have a FastCS project set up:

- **Create an EPICS IOC**: See [](create-epics-ioc-with-ca-and-pva.md) for building EPICS IOCs
- **Learn FastCS basics**: See [](../tutorials/static-drivers.md) for controller fundamentals
- **Add device communication**: Implement connection classes and AttributeIO
- **Write tests**: Use pytest to test your controllers
- **Set up CI/CD**: GitHub Actions workflows are already configured

## See Also

- [](../tutorials/installation.md) - Alternative installation methods
- [](create-epics-ioc-with-ca-and-pva.md) - Building EPICS IOCs with FastCS
- [FastCS GitHub](https://github.com/DiamondLightSource/FastCS) - Source code and examples
- [Python Copier Template](https://github.com/DiamondLightSource/python-copier-template) - Template documentation
