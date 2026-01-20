# 9. Replace Handler with AttributeIO/AttributeIORef Pattern

Date: 2025-10-03

**Related:** [PR #218](https://github.com/DiamondLightSource/FastCS/pull/218)

## Status

Accepted

## Context

Currently the `Handler` pattern is used to manage attribute I/O operations. This design has several classes:

- `AttrHandlerR` previously `Updater` - Protocol for reading/updating attribute values
- `AttrHandlerW` previously `Sender` - Protocol for writing/setting attribute values
- `AttrHandlerRW` previously `Handler` - Combined read-write handler
- `SimpleAttrHandler` - Basic implementation for internal parameters

There are a few limitations with this architecture:

1. **Handler Instance per Attribute:** Every attribute needed its own Handler instance because that's where the specification connecting the attribute to a unique resource live is defined. This means redundant Handler instances when multiple attributes use the same I/O pattern

2. **Circular Reference Loop:** The architecture has circular dependencies:
   - Controller → Attributes (controller owns attributes)
   - Attributes → Handlers (each attribute has a handler)
   - Handlers → Controller (handlers need controller reference to communicate with device)

3. **Tight Coupling to Controllers:** Handlers need direct references to Controllers, coupling I/O logic to the controller structure rather than just to the underlying connections (e.g., hardware interfaces, network connections)

4. **Mixed Concerns:** Handlers combine resource specification (what to connect to) with I/O behavior (how to read/write), making both harder to reason about

The system needs a more flexible way to:
- Share a single AttributeIO instance across multiple attributes
- Use lightweight AttributeIORef instances to specify resource connections per-attribute
- Break the circular dependency chain
- Validate that Controllers have exactly one AttributeIO to handle each Attribute
- Separate resource specification from I/O behavior

## Decision

Replace the `Handler` pattern with a two-component system: `AttributeIO` for behavior and `AttributeIORef` for configuration.

Key architectural changes:

1. **AttributeIORef** - Lightweight resource specification per-attribute:
   - Lightweight dataclass specifying resource connection details
   - Can be subclassed to add fields like resource names, register addresses, etc.
   - Attributes have unique AttributeIORef instances
   - Dynamically connected to a single AttributeIO instance at runtime

2. **AttributeIO** - Shared I/O behavior:
   - Single instance per Controller handles multiple Attributes
   - Generic class parameterized by data type `T` and reference type `AttributeIORefT`
   - Accesses the AttributeIORef from the attribute to know which resource to access
   - Only needs to know about connections, not controllers

3. **Parameterized Attributes:**
   - Attributes are now parameterized with `AttributeIORef` types
   - `AttrR[T, AttributeIORefT]` - Read-only attribute with typed I/O reference
   - `AttrRW[T, AttributeIORefT]` - Read-write attribute with typed I/O reference
   - Type system ensures matching between AttributeIO and AttributeIORef

4. **Initialization Validation:**
   - Controller validates at initialization that it has exactly one AttributeIO to handle each Attribute
   - Ensures all attributes are properly connected before serving the Controller API

## Consequences

### Migration Impact

Users and developers need to:

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
