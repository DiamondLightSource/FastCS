# 9. Replace Handler with AttributeIO/AttributeIORef Pattern

Date: 2025-10-03

**Related:** [PR #218](https://github.com/DiamondLightSource/FastCS/pull/218)

## Status

Accepted

## Context

In the original FastCS architecture, the `Handler` pattern was used to manage attribute I/O operations. The design had several classes:

**Original Handler Architecture:**
- `AttrHandlerR` previously `Updater` - Protocol for reading/updating attribute values
- `AttrHandlerW` previously `Sender` - Protocol for writing/setting attribute values
- `AttrHandlerRW` previously `Handler` - Combined read-write handler
- `SimpleAttrHandler` - Basic implementation for internal parameters

**Limitations of the Handler Pattern:**

1. **Handler Instance per Attribute:** Every attribute needed its own Handler instance because that's where the specification connecting the attribute to a unique resource lived. This created:
   - Heavy memory overhead for controllers with many attributes
   - Redundant Handler instances when multiple attributes used the same I/O pattern
   - Difficulty sharing I/O logic across attributes

2. **Circular Reference Loop:** The architecture created circular dependencies:
   - Controller → Attributes (controller owns attributes)
   - Attributes → Handlers (each attribute has a handler)
   - Handlers → Controller (handlers need controller reference to communicate with device)

3. **Tight Coupling to Controllers:** Handlers needed direct references to Controllers, coupling I/O logic to the controller structure rather than just to the underlying connections (e.g., hardware interfaces, network connections)

4. **Mixed Concerns:** Handlers combined resource specification (what to connect to) with I/O behavior (how to read/write), making both harder to reason about

The system needed a more flexible way to:
- Share a single AttributeIO instance across multiple attributes
- Use lightweight AttributeIORef instances to specify resource connections per-attribute
- Break the circular dependency chain
- Validate that Controllers have exactly one AttributeIO to handle each Attribute
- Separate resource specification from I/O behavior

## Decision

We replaced the `Handler` pattern with a two-component system: `AttributeIO` for behavior and `AttributeIORef` for configuration.

### New Architecture

1. **AttributeIORef - Lightweight Resource Specification:**
```python
@dataclass(kw_only=True)
class AttributeIORef:
    update_period: float | None = None
```
   - Lightweight dataclass specifying resource connection details per-attribute
   - Can be subclassed to add fields like resource names, register addresses, etc.
   - Multiple attributes can have their own AttributeIORef instances
   - Dynamically connected to a single AttributeIO instance at runtime

2. **AttributeIO - Shared I/O Behavior:**
```python
class AttributeIO(Generic[T, AttributeIORefT]):
    async def update(self, attr: AttrR[T, AttributeIORefT]) -> None:
        raise NotImplementedError()

    async def send(self, attr: AttrRW[T, AttributeIORefT], value: T) -> None:
        raise NotImplementedError()
```
   - Single instance per Controller can handle multiple Attributes
   - Generic class parameterized by data type `T` and reference type `AttributeIORefT`
   - Receives the AttributeIORef for each attribute to know which resource to access
   - Only needs to know about connections (e.g. resource name, hardware interface)

3. **Parameterized Attributes:**
   - Attributes are now parameterized with `AttributeIORef` types
   - `AttrR[T, AttributeIORefT]` - Read-only attribute with typed I/O reference
   - `AttrRW[T, AttributeIORefT]` - Read-write attribute with typed I/O reference
   - Type system ensures matching between AttributeIO and AttributeIORef

4. **Initialization Validation:**
   - Controller validates at initialization that it has exactly one AttributeIO to handle each Attribute
   - Ensures all attributes are properly connected before the serving the Controller API

### Key Improvements

- **Breaks Circular Dependencies:** AttributeIO only needs connections, not Controllers
- **Memory Efficiency:** Single AttributeIO instance serves many Attributes
- **Separation of Concerns:**
  - AttributeIORef: lightweight resource specification (what to connect to)
  - AttributeIO: shared I/O behavior (how to read/write)
- **Validated Coverage:** Initialization ensures every Attribute has an AttributeIO handler
- **Type Safety:** Generic types ensure AttributeIO and AttributeIORef match
- **Extensibility:** Easy to create custom Ref types with resource-specific fields

## Consequences

### Technical Changes

- 519 insertions, 290 deletions across 20 files
- Created new files:
  - `src/fastcs/attribute_io.py` - AttributeIO base class
  - `src/fastcs/attribute_io_ref.py` - AttributeIORef base class
- Updated attribute system to use generic parameterization
- Refactored all tests to use new pattern
- Updated callbacks to `AttrUpdateCallback` and `AttrSetCallback`

### Migration Impact

Users and developers needed to:

**Before (Handler pattern - one instance per attribute):**
```python
# Temperature controller that communicates via TCP/IP
class TempControllerHandler(AttrHandlerRW):
    def __init__(self, register_name: str, controller: TempController):
        self.register_name = register_name
        self.connection = connection
        self.update_period = 0.2
        self.controller = controller

    async def initialise(self, controller):
        self.controller_ref = controller  # Creates circular dependency

    async def update(self, attr):
        # Each attribute needs its own handler instance
        query = f"{self.register_name}?"
        response = await self.connection.send_query(f"{query}\r\n")
        value = float(response.strip())
        await attr.set(value)

    async def put(self, attr, value):
        command = f"{self.register_name}={value}"
        await self.connection.send_command(f"{command}\r\n")

controller = TempController()
ramp_rate = AttrRW(Float(), handler=TempControllerHandler("R", controller))
power = AttrR(Float(), handler=TempControllerHandler("P", controller))
setpoint = AttrRW(Float(), handler=TempControllerHandler("S", controller))
```

**After (AttributeIO pattern - shared instance):**
```python
@dataclass
class TempControllerIORef(AttributeIORef):
    name: str  # Register name like "R", "P", "S"
    update_period: float = 0.2

class TempControllerAttributeIO(AttributeIO[float, TempControllerIORef]):
    def __init__(self, connection: IPConnection):
        self.connection = connection

    async def update(self, attr: AttrR[float, TempControllerIORef]) -> None:
        query = f"{attr.io_ref.name}?"
        response = await self.connection.send_query(f"{query}\r\n")
        value = float(response.strip())
        await attr.update(value)

    async def send(self, attr: AttrRW[float, TempControllerIORef], value: float) -> None:
        command = f"{attr.io_ref.name}={value}"
        await self.connection.send_command(f"{command}\r\n")

connection = IPConnection()
temp_io = TempControllerAttributeIO(connection)
ramp_rate = AttrRW(Float(), io_ref=TempControllerIORef(name="R"))
power = AttrR(Float(), io_ref=TempControllerIORef(name="P"))
setpoint = AttrRW(Float(), io_ref=TempControllerIORef(name="S"))
```

This decision established a more flexible, type-safe foundation for attribute I/O operations, enabling better extensibility and maintainability for controller implementations.
