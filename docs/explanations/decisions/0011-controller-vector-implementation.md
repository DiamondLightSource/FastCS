# 11. Introduce ControllerVector for Indexed Sub-Controllers

Date: 2025-11-10

**Related:** [PR #192](https://github.com/DiamondLightSource/FastCS/pull/192)

## Status

Accepted

## Context

After removing the `SubController` class (ADR-0010), FastCS had a unified `Controller` class that could be used in both top-level and nested contexts. However, a common use case remained unaddressed: managing collections of identical sub-controllers distinguished only by an integer index.

**Common Use Case - Multiple Identical Components:**

Many devices have multiple identical components that need individual control:
- Multi-axis motion stages (X, Y, Z axes)
- Multi-channel power supplies (Channel 1, 2, 3, ...)
- Temperature controller ramp profiles (Ramp 1, 2, 3, ...)
- Camera ROI regions (ROI 0, 1, 2, ...)

**Original Approach - Manual Registration:**

Before ControllerVector, developers had to manually register each indexed controller:

```python
class MotorController(Controller):
    position = AttrRW(Float())
    velocity = AttrRW(Float())

class StageController(Controller):
    def __init__(self, num_axes: int):
        super().__init__()
        self._motors: list[MotorController] = []

        # Manual registration for each axis
        for i in range(num_axes):
            motor = MotorController()
            self._motors.append(motor)
            self.add_sub_controller(f"Axis{i}", motor)  # String-based naming
```

**Problems with Manual Registration:**

1. **No Collection Semantics:** Controllers registered with string names (`"Axis0"`, `"Axis1"`) didn't behave like a natural collection. No iteration, indexing, or length operations.

2. **String-Based Indexing:** Accessing controllers required string manipulation: `controller.sub_controllers["Axis0"]` instead of natural indexing: `controller.axes[0]`

The system needed a dedicated pattern for indexed collections that:
- Provides natural collection semantics
- Enforces integer-based indexing
- Generates a clear PVI structure for clients and UI generation
- Reduces boilerplate for common patterns

## Decision

We introduced `ControllerVector`, a specialized controller type for managing collections of indexed sub-controllers with dict-like semantics.

### Key Features

1. **MutableMapping Interface:**
   - Implements `__getitem__`, `__setitem__`, `__iter__`, `__len__`
   - Provides dict-like access: `vector[0]`, `vector[1]`, etc.
   - Supports iteration: `for index, controller in vector.items()`

2. **Type-Safe Integer Indexing:**
   - Keys must be integers (enforced by type hints and runtime checks)
   - Values must be Controller instances
   - Clear error messages for type violations

3. **Non-Contiguous Indices:**
   - Indices don't need to be sequential: `{1: motor1, 5: motor5, 10: motor10}` is valid
   - Useful for sparse collections or specific numbering schemes

4. **Inherits from BaseController:**
   - Can have its own attributes alongside indexed sub-controllers
   - Can be nested within other controllers

### Usage Pattern

**With ControllerVector:**

```python
class MotorController(Controller):
    position = AttrRW(Float())
    velocity = AttrRW(Float())

class AxesVector(ControllerVector):
    """Vector of motor axes with shared attributes"""
    enabled = AttrRW(Bool())  # Shared attribute for all axes

class StageController(Controller):
    def __init__(self, num_axes: int):
        super().__init__()

        # Create vector with indexed motors
        motors = {i: MotorController() for i in range(num_axes)}
        self.axes = AxesVector(motors, description="Motor axes")

        # Natural collection access
        first_axis = self.axes[0]
        for i, motor in self.axes.items():
            print(f"Motor {i}: {motor}")
```

**Alternative Inline Usage:**

```python
class StageController(Controller):
    def __init__(self, num_axes: int):
        super().__init__()

        # Direct ControllerVector instantiation
        self.axes = ControllerVector(
            {i: MotorController() for i in range(num_axes)},
            description="Motor axes"
        )
```

### Benefits

- **Natural Collection Semantics:** Dict-like interface provides familiar indexing, iteration, and length operations

- **Consistency:** Integer-only keys prevent naming inconsistencies

- **Clear Intent:** ControllerVector explicitly signals "collection of identical components"

- **Sparse Collections:** Non-contiguous indices support flexible numbering schemes

## Consequences

### Technical Changes

- 408 insertions, 315 deletions across 12 files
- Created `src/fastcs/controllers/controller_vector.py` with ControllerVector class
- Updated `src/fastcs/controller_api.py` to handle ControllerVector
- Enhanced EPICS PVI generation in `src/fastcs/transport/epics/pva/pvi.py`
- Simplified `src/fastcs/transport/epics/pva/pvi_tree.py` (207 lines removed)
- Updated EPICS CA and PVA IOC implementations
- Updated test examples to demonstrate ControllerVector usage

### Migration Impact

For controller developers with indexed collections:

**Before (Manual registration):**
```python
class Controller:
    def __init__(self):
        super().__init__()
        for i in range(4):
            channel = ChannelController()
            self.add_sub_controller(f"Ch{i}", channel)

        # Access via string keys
        first = self.sub_controllers["Ch0"]
```

**After (ControllerVector):**
```python
class Controller:
    def __init__(self):
        super().__init__()
        self.channels = ControllerVector(
            {i: ChannelController() for i in range(4)},
            description="Power supply channels"
        )

        # Natural dict-like access
        first = self.channels[0]
        for i, channel in self.channels.items():
            ...
```

### Design Patterns Enabled

**1. Subclassed Vectors with Shared Attributes:**
```python
class ChannelVector(ControllerVector):
    master_enable = AttrRW(Bool())  # Shared across all channels

    def __init__(self, num_channels: int):
        channels = {i: ChannelController(i) for i in range(num_channels)}
        super().__init__(channels, description="Power channels")
```

**2. Sparse Indexing:**
```python
# Non-contiguous indices for specific addressing schemes
rois = ControllerVector({
    1: ROIController(),
    5: ROIController(),
    10: ROIController()
})
```

### Architectural Impact

The introduction of ControllerVector established a clear pattern for managing collections of identical components, reducing boilerplate while improving type safety and UI generation capabilities.
