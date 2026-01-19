# 10. Remove SubController Class

Date: 2025-10-01

**Related:** [PR #222](https://github.com/DiamondLightSource/FastCS/pull/222)

## Status

Accepted

## Context

FastCS originally provided two separate classes for building controller hierarchies: `Controller` for top-level device controllers and `SubController` for nested components within a controller.

**Original Architecture - Separate Classes:**

```python
class Controller(BaseController):
    """Top-level controller for a device."""
    def __init__(self, description: str | None = None) -> None:
        super().__init__(description=description)
    async def connect(self) -> None:
        pass

class SubController(BaseController):
    """A subordinate to a Controller for managing a subset of a device."""
    root_attribute: Attribute | None = None
    def __init__(self, description: str | None = None) -> None:
        super().__init__(description=description)
```

The key distinctions were
- `SubController` had a `root_attribute` property for exposing a single attribute to its
  parent
- Only `Controller` could be used as the root of the hierarchy

Type annotations enforced the hierarchy:

```python
# In BaseController
def register_sub_controller(self, name: str, sub_controller: SubController):
    """Only accepts SubController instances"""
    ...
```

**Usage Pattern:**
```python
class TemperatureRampController(SubController):  # Must use SubController
    start = AttrRW(Int())
    end = AttrRW(Int())

class TemperatureController(Controller):  # Must use Controller
    def __init__(self):
        super().__init__()
        ramp = TemperatureRampController()
        self.register_sub_controller("Ramp1", ramp)
```

**Problems with Two-Class Hierarchy:**

1. **Unnecessary Type Coupling:** The classes were functionally identical. Having two classes created artificial separation without meaningful functional benefit.

2. **Design-Time Commitment:** Developers had to choose `Controller` vs `SubController` at class definition time, before knowing all the contexts where the component might be used. A component designed as standalone might later need to become nested, forcing inheritance changes.

3. **Reduced Reusability:** Controllers written as `SubController` couldn't be used as top-level controllers without changing their base class, and vice versa. This coupling hurt composition flexibility.

The system needed a way to support hierarchical composition without committing to hierarchy at class definition time.

## Decision

We unified `Controller` and `SubController` into a single `Controller` class that can be used in both top-level and nested contexts.

### New Architecture

**Unified Controller Class:**

```python
class Controller(BaseController):
    """Controller for a device or device component."""

    root_attribute: Attribute | None = None  # NOW on Controller

    def __init__(self, description: str | None = None) -> None:
        super().__init__(description=description)

    async def connect(self) -> None:
        pass
```

**Updated BaseController Type Annotations:**

```python
# In BaseController
def add_sub_controller(self, name: str, sub_controller: Controller):
    """Now accepts any Controller instance"""
    ...

def get_sub_controllers(self) -> dict[str, Controller]:
    """Returns Controller instances"""
    return self.__sub_controller_tree
```

### Key Changes

1. **Single Unified Class:**
   - Removed `SubController` class entirely
   - Moved `root_attribute` property to `Controller`
   - Controller can now be used in any context

2. **Usage-Based Hierarchy:**
   - Whether a Controller is "top-level" or "nested" is determined by how it's used, not by its class
   - Same Controller class can be instantiated standalone or nested in another Controller

3. **Flexible Composition:**
   - Any Controller can be added as a sub-controller to another Controller
   - No inheritance changes needed to repurpose a controller
   - Composition determined at instantiation, not class definition

4. **Simplified API:**
   - One class to understand and import
   - Consistent patterns across all controller definitions
   - Type annotations simplified throughout codebase

### Migration Pattern:

**Before (Two Classes):**
```python
from fastcs import Controller, SubController

class RampController(SubController):  # Forced to use SubController
    start = AttrRW(Int())
    end = AttrRW(Int())

class TempController(Controller):  # Forced to use Controller
    def __init__(self):
        super().__init__()
        self.register_sub_controller("Ramp1", RampController())
```

**After (One Class):**
```python
from fastcs import Controller

class RampController(Controller):  # Just use Controller
    start = AttrRW(Int())
    end = AttrRW(Int())

class TempController(Controller):  # Just use Controller
    def __init__(self):
        super().__init__()
        self.add_sub_controller("Ramp1", RampController())
```

`RampController` could then be used as a the root controller.

### Benefits

- **Composition over Inheritance:** Hierarchy determined by usage, not class definition

- **Increased Reusability:** Controllers can be used in any context without refactoring

- **Simpler Mental Model:** One class for all controller use cases

- **Reduced Coupling:** No design-time commitment to hierarchy level

- **Easier Evolution:** Controllers can start standalone and be nested later without code changes

- **Consistent API:** Single class reduces cognitive load for developers

## Consequences

### Technical Changes

- 30 insertions, 43 deletions
- Removed `SubController` class from `src/fastcs/controller.py`
- Added `root_attribute` property to `Controller` class
- Updated type annotations throughout codebase: `SubController` → `Controller`
- Updated method signatures in `src/fastcs/controllers/base_controller.py`
- Renamed `register_sub_controller` to `add_sub_controller` for consistency
- Updated documentation and examples
- Updated all test files to use unified `Controller` class

### Migration Impact

For controller developers:
1. Replace all `class MyController(SubController)` with `class MyController(Controller)`
2. Replace `register_sub_controller()` calls with `add_sub_controller()`
3. No functional changes required - same composition patterns work

For existing codebases:
- Simple find-and-replace migration: `SubController` → `Controller`
- Backward compatible: composition patterns unchanged
- Controllers previously written as `Controller` or `SubController` now uniformly use `Controller`

### Architectural Impact

This decision reinforced the composition-over-inheritance principle in FastCS. The removal of `SubController` flattened the inheritance hierarchy while maintaining full composition capabilities, making FastCS controllers more flexible and easier to compose in different contexts.
