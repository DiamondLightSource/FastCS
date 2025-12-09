# Creating an EPICS IOC with CA and PVA Transports

## Overview

FastCS enables you to create EPICS IOCs that support both Channel Access (CA) and PV Access (PVA) protocols simultaneously. This guide shows you how to build a production-ready IOC and how to migrate existing EPICS IOCs to FastCS.

**When to use each protocol:**
- **Channel Access (CA)**: Legacy compatibility, widely supported, proven reliability
- **PV Access (PVA)**: Structured data, better performance, modern features
- **Both**: Maximum compatibility, transition period, different clients prefer different protocols

## Prerequisites

- A FastCS project set up with EPICS support (`fastcs[epicsca,epicspva]`)
- Basic understanding of EPICS concepts (PVs, records, protocols)
- Knowledge of your device's control interface (serial, TCP/IP, etc.)

**If you haven't set up a FastCS project yet**, see [](create-new-fastcs-project.md) first.

## Step 1: Define Your Controller

The `Controller` class is the core of your FastCS IOC. It represents your device and defines all its attributes and methods.

### Create Basic Controller

Create a file `my_device.py`:

```python
from fastcs.attributes import AttrR, AttrW, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Float, Int, String

class MyDeviceController(Controller):
    """Controller for My Device."""

    # Read-only attributes
    device_id: AttrR = AttrR(String(), description="Device serial number")
    temperature: AttrR = AttrR(Float(), description="Current temperature in °C")
    status: AttrR = AttrR(Bool(), description="Device status")

    # Read-write attributes
    setpoint: AttrRW = AttrRW(Float(), description="Temperature setpoint in °C")
    enable: AttrRW = AttrRW(Bool(), description="Enable/disable device")

    # Write-only attributes (commands)
    reset: Command = Command(Bool(), description="Reset device")
```

### Understanding Attribute Types

FastCS provides three attribute access modes:

- **`AttrR`**: Read-only attributes
- **`AttrW`**: Write-only attributes
- **`AttrRW`**: Read-write attributes (creates separate readback PVs)

### Common Data Types

```python
from fastcs.datatypes import Bool, Float, Int, String, Enum, Waveform

# Boolean
enabled = AttrRW(Bool())

# Numeric with precision
temperature = AttrR(Float())  # Default precision
precision = AttrR(Float())    # Use PV precision field for display

# Integer
count = AttrR(Int())

# String
status_msg = AttrR(String())

# Enumeration
from enum import Enum as PyEnum

class DeviceState(PyEnum):
    IDLE = 0
    RUNNING = 1
    ERROR = 2

state = AttrR(Enum(DeviceState))

# Waveform (arrays)
import numpy as np
waveform = AttrR(Waveform(np.dtype("f"), shape=(1024,768) ))  # Float array
```

## Step 2: Implement Device Communication

### Create Connection Class

For TCP/IP devices, use FastCS's built-in `IPConnection`:

```python
from fastcs.connections import IPConnection, IPConnectionSettings

class MyDeviceController(Controller):
    def __init__(self, settings: IPConnectionSettings):
        self._connection = IPConnection()
        self._settings = settings
        super().__init__()

    async def connect(self):
        """Called by FastCS during startup."""
        await self._connection.connect(self._settings)
```

For other connection types (serial, USB, etc.), create a custom connection class following the async pattern.

### Implement AttributeIO for Device Communication

`AttributeIO` handles reading and writing values to your device:

```python
from dataclasses import dataclass
from typing import TypeVar
from fastcs.attributes import AttributeIO, AttributeIORef

NumberT = TypeVar("NumberT", int, float)

@dataclass
class DeviceAttributeIORef(AttributeIORef):
    """Reference for device attribute IO operations."""
    command: str  # Device protocol command
    update_period: float | None = 1.0  # Poll every second

class DeviceAttributeIO(AttributeIO[NumberT, DeviceAttributeIORef]):
    """Handles reading from and writing to the device."""

    def __init__(self, connection: IPConnection):
        super().__init__()
        self._connection = connection

    async def update(self, attr: AttrR[NumberT, DeviceAttributeIORef]):
        """Read value from device and update attribute."""
        # Send query to device
        response = await self._connection.send_query(
            f"{attr.io_ref.command}?\r\n"
        )
        # Parse response and update attribute
        value = response.strip()
        await attr.update(value)

    async def send(self, attr):
        """Write attribute value to device."""
        command = f"{attr.io_ref.command}={attr.get()}\r\n"
        await self._connection.send_command(command)
```

### Connect Attributes to Device IO

```python
from fastcs.attributes import AttrR, AttrRW

class MyDeviceController(Controller):
    # Attribute with IO reference
    temperature = AttrR(
        Float(),
        io_ref=DeviceAttributeIORef(command="TEMP", update_period=0.5)
    )

    setpoint: AttrRW = AttrRW(
        Float(),
        io_ref=DeviceAttributeIORef(command="SETP", update_period=1.0)
    )

    def __init__(self, host: str, port: int):
        self._connection = IPConnection()
        self._settings = IPConnectionSettings(host, port)

        # Pass IO handler to controller
        device_io = DeviceAttributeIO(self._connection)
        super().__init__(ios=[device_io])

    async def connect(self):
        await self._connection.connect(self._settings)
```

### Handle Errors Appropriately

```python
class DeviceAttributeIO(AttributeIO[NumberT, DeviceAttributeIORef]):
    async def update(self, attr):
        try:
            response = await self._connection.send_query(
                f"{attr.io_ref.command}?\r\n"
            )
            value = attr.dtype(response.strip())
            await attr.update(value)
        except ConnectionError:
            # Connection errors are logged but don't crash the IOC
            raise
        except ValueError as e:
            # Invalid response from device
            raise ValueError(f"Invalid response for {attr.io_ref.command}: {e}")
```

## Step 3: Set Up Channel Access Transport

Configure the CA transport with your PV prefix:

```python
from pathlib import Path
from fastcs.transports import EpicsCATransport, EpicsIOCOptions, EpicsGUIOptions

# Basic CA transport
ca_transport = EpicsCATransport(
    epicsca=EpicsIOCOptions(pv_prefix="MY-DEVICE")
)

# With GUI generation (Phoebus .bob file)
ca_transport = EpicsCATransport(
    epicsca=EpicsIOCOptions(pv_prefix="MY-DEVICE"),
    gui=EpicsGUIOptions(
        output_path=Path("./my_device.bob"),
        title="My Device Control"
    )
)
```

### PV Naming Convention

With `pv_prefix="MY-DEVICE"`, PVs will be named:
- `MY-DEVICE:DeviceId` (from `device_id` attribute)
- `MY-DEVICE:Temperature` (from `temperature` attribute)
- `MY-DEVICE:Setpoint` (demand value)
- `MY-DEVICE:Setpoint_RBV` (readback value for AttrRW)

Sub-controllers create hierarchical PV names:
- `MY-DEVICE:SubController:AttributeName`

## Step 4: Set Up PV Access Transport

Add PVA transport for modern EPICS clients:

```python
from fastcs.transports import EpicsPVATransport

# Basic PVA transport
pva_transport = EpicsPVATransport(
    epicspva=EpicsIOCOptions(pv_prefix="MY-DEVICE")
)

# With GUI generation
pva_transport = EpicsPVATransport(
    epicspva=EpicsIOCOptions(pv_prefix="MY-DEVICE"),
    gui=EpicsGUIOptions(
        output_path=Path("./my_device_pva.bob"),
        title="My Device Control (PVA)"
    )
)
```

**Note**: You can use the same PV prefix for both CA and PVA, or use different prefixes if you need to distinguish between protocols.

## Step 5: Launch with Multiple Transports

Bring it all together in your main script:

```python
from pathlib import Path
from fastcs.launch import FastCS
from fastcs.transports import (
    EpicsCATransport,
    EpicsPVATransport,
    EpicsIOCOptions,
    EpicsGUIOptions,
)

# Configure transports
ca_transport = EpicsCATransport(
    epicsca=EpicsIOCOptions(pv_prefix="MY-DEVICE"),
    gui=EpicsGUIOptions(
        output_path=Path("./my_device_ca.bob"),
        title="My Device (CA)"
    )
)

pva_transport = EpicsPVATransport(
    epicspva=EpicsIOCOptions(pv_prefix="MY-DEVICE"),
    gui=EpicsGUIOptions(
        output_path=Path("./my_device_pva.bob"),
        title="My Device (PVA)"
    )
)

# Create controller instance
controller = MyDeviceController(host="192.168.1.100", port=5000)

# Launch FastCS with both transports
fastcs = FastCS(controller, [ca_transport, pva_transport])

if __name__ == "__main__":
    fastcs.run()
```

## Step 6: Testing Your IOC

### Start the IOC

```bash
# Use uv
uv run my-device
```

You should see output indicating both transports are running:

```
INFO: Running IOC pv_prefix=MY-DEVICE
INFO: Running IOC pv_prefix=MY-DEVICE
```

### Test Channel Access PVs

```bash
# List all PVs with your prefix
caget MY-DEVICE:DeviceId MY-DEVICE:Temperature MY-DEVICE:Setpoint_RBV

# Set a value
caput MY-DEVICE:Setpoint 25.5

# Monitor a PV
camonitor MY-DEVICE:Temperature
```

### Test PV Access PVs

```bash
# Get PV value
pvget MY-DEVICE:Temperature

# Set a value
pvput MY-DEVICE:Setpoint 25.5

# Monitor a PV
pvmonitor MY-DEVICE:Temperature
```

### Test with Phoebus

1. The `.bob` files are generated in your current directory
2. Open Phoebus/CS-Studio
3. File → Open → Select the generated `.bob` file
4. The GUI shows all your device attributes with appropriate widgets

### Verify Both Protocols Work

Run both commands simultaneously to confirm both transports serve the same data:

```bash
# Terminal 1: Monitor via CA
camonitor MY-DEVICE:Temperature

# Terminal 2: Monitor via PVA
pvmonitor MY-DEVICE:Temperature

# Terminal 3: Set value via CA
caput MY-DEVICE:Setpoint 30.0
```

Both monitors should show the updated value.

## Step 7: Advanced Configuration

### Setting Different Update Periods

```python
class MyDeviceController(Controller):
    # Fast updates for critical parameters
    temperature: AttrR = AttrR(
        Float(),
        io_ref=DeviceAttributeIORef(command="TEMP", update_period=0.1)
    )

    # Slow updates for status
    device_id: AttrR = AttrR(
        String(),
        io_ref=DeviceAttributeIORef(command="ID", update_period=10.0)
    )

    # No automatic updates (manual update only)
    firmware_version: AttrR = AttrR(
        String(),
        io_ref=DeviceAttributeIORef(command="FW", update_period=None)
    )
```

### Organizing with Sub-Controllers

For complex devices with multiple components:

```python
class PowerSupplyController(Controller):
    """Power supply sub-system."""
    voltage: AttrRW = AttrRW(Float())
    current: AttrRW = AttrRW(Float())

class MyDeviceController(Controller):
    """Main device controller."""
    device_id: AttrR = AttrR(String())

    def __init__(self, host: str, port: int):
        self._connection = IPConnection()
        super().__init__()

        # Add sub-controller
        self.psu = PowerSupplyController()
```
        self.psu = PowerSupplyController()
- `MY-DEVICE:Psu:Voltage`
- `MY-DEVICE:Psu:Current`

### Using Methods for Commands

For complex operations beyond simple attribute writes:

```python
from fastcs.methods import command

class MyDeviceController(Controller):
    @command()
    async def calibrate(self) -> None:
        """Run device calibration procedure."""
        await self._connection.send_command("CALIBRATE\r\n")

    @command()
    async def home_motors(self) -> None:
        """Home all motors."""
        await self._connection.send_command("HOME\r\n")
```

This creates PVs:
- `MY-DEVICE:Calibrate` (write 1 to execute)
- `MY-DEVICE:HomeMotors` (write 1 to execute)

### Implementing Scan Methods

For periodic operations that don't fit the AttributeIO pattern:

```python
from fastcs.methods import scan

class MyDeviceController(Controller):
    error_count: AttrR = AttrR(Int())

    @scan(0.5)  # Run every 0.5 seconds
    async def check_errors(self):
        """Poll device error status."""
        response = await self._connection.send_query("ERRORS?\r\n")
        error_count = int(response.strip())
        await self.error_count.update(error_count)
```

## Converting an Existing EPICS IOC to FastCS

### Step 1: Analyze Your Current Implementation

Identify the key components:

1. **Database files** (`.db`, `.template`): Define your records
2. **Device support**: C/C++ code or asynDriver configuration
3. **Protocol files**: StreamDevice protocols or custom communication
4. **Startup scripts**: IOC initialization

### Step 2: Map EPICS Records to FastCS Attributes

| EPICS Record Type | FastCS Equivalent | Notes |
|------------------|-------------------|-------|
| `ai` (Analog Input) | `AttrR(Float())` | Read-only numeric |
| `ao` (Analog Output) | `AttrRW(Float())` | Read-write numeric, creates `_RBV` |
| `bi` (Binary Input) | `AttrR(Bool())` | Read-only boolean |
| `bo` (Binary Output) | `AttrRW(Bool())` | Read-write boolean |
| `stringin` | `AttrR(String())` | Read-only string |
| `stringout` | `AttrRW(String())` | Read-write string |
| `longin` | `AttrR(Int())` | Read-only integer |
| `longout` | `AttrRW(Int())` | Read-write integer |
| `mbbi` (Multi-bit Binary Input) | `AttrR(Enum(...))` | Read-only enumeration |
| `mbbo` (Multi-bit Binary Output) | `AttrRW(Enum(...))` | Read-write enumeration |
| `waveform` | `AttrR(Waveform(...))` or `AttrRW(Waveform(...))` | Arrays |
| `calc`, `calcout` | Use Python logic in controller | Calculations in code |

### Step 3: Example Conversion

**Original EPICS Database (`.db` file):**

```
record(ai, "$(P):TEMPERATURE") {
    field(DTYP, "asynFloat64")
    field(INP, "@asyn($(PORT)) TEMP")
    field(SCAN, "1 second")
    field(PREC, "2")
    field(EGU, "°C")
}

record(ao, "$(P):SETPOINT") {
    field(DTYP, "asynFloat64")
    field(OUT, "@asyn($(PORT)) SETP")
    field(PREC, "2")
    field(EGU, "°C")
}

record(stringin, "$(P):ID") {
    field(DTYP, "asynOctetRead")
    field(INP, "@asyn($(PORT)) ID")
}
```

**Equivalent FastCS Controller:**

```python
from fastcs.attributes import AttrR, AttrRW
from fastcs.datatypes import Float, String
from fastcs.controllers import Controller

class TemperatureController(Controller):
    """Temperature controller - replaces EPICS database."""

    # Read-only temperature (ai record)
    temperature: AttrR = AttrR(
        Float(),
        description="Current temperature in °C",
        io_ref=DeviceAttributeIORef(command="TEMP", update_period=1.0)
    )

    # Read-write setpoint (ao record)
    setpoint: AttrRW = AttrRW(
        Float(),
        description="Temperature setpoint in °C",
        io_ref=DeviceAttributeIORef(command="SETP", update_period=1.0)
    )

    # Read-only ID (stringin record)
    device_id: AttrR = AttrR(
        String(),
        description="Device identifier",
        io_ref=DeviceAttributeIORef(command="ID", update_period=10.0)
    )
```

**Notes on the conversion:**
- `SCAN` field → `update_period` in `io_ref`
- `PREC`, `EGU` fields → Handle in EPICS client display (Phoebus, etc.)
- `DTYP` and `INP`/`OUT` → Implemented in `AttributeIO`
- `ao` records automatically get `_RBV` readback with `AttrRW`

### Step 4: Convert Device Support Code

**Original asynDriver-based device support:**

```c
// In device support or asynDriver code
asynStatus readFloat64(void *drvPvt, asynUser *pasynUser,
                       epicsFloat64 *value) {
    char response[256];
    // Send command to device
    pasynOctet->write(pasynUser, "TEMP?\r\n", 7, &written);
    // Read response
    pasynOctet->read(pasynUser, response, sizeof(response), &nread);
    *value = atof(response);
    return asynSuccess;
}
```

**Equivalent FastCS AttributeIO:**

```python
class DeviceAttributeIO(AttributeIO):
    async def update(self, attr):
        """Read value from device."""
        command = f"{attr.io_ref.command}?\r\n"
        response = await self._connection.send_query(command)
        value = attr.dtype(response.strip())
        await attr.update(value)
```

### Step 5: Migration Strategy

1. **Parallel Development**:
   - Keep existing IOC running
   - Develop FastCS version alongside
   - Test thoroughly before switching

2. **Incremental Migration**:
   - Start with read-only attributes
   - Add write functionality
   - Port complex commands last
   - Test each phase

3. **Testing Checklist**:
   - ✓ All PVs accessible via `caget`/`pvget`
   - ✓ Write operations work via `caput`/`pvput`
   - ✓ Update rates match requirements
   - ✓ Error handling works correctly
   - ✓ Existing control system scripts still work
   - ✓ GUIs display correctly


### Benefits of Migration

- **Less boilerplate**: No separate database and device support files
- **Python ecosystem**: Use standard Python tools and libraries
- **Better testing**: Unit test controllers with standard Python tools
- **Multi-protocol**: Serve CA, PVA, Tango, REST, GraphQL simultaneously
- **Type safety**: Python type hints catch errors early
- **Easier maintenance**: Single language (Python) for device logic

## Troubleshooting

### PVs Not Appearing

**Problem**: `caget MY-DEVICE:Temperature` returns "Channel connect timed out"

**Solutions**:
- Check `EPICS_CA_ADDR_LIST` environment variable
- Verify PV prefix matches (case-sensitive)
- Ensure IOC is running: look for "Running IOC" in logs
- Check firewall allows EPICS CA ports (5064-5065)

### Connection Errors

**Problem**: `ConnectionError` when IOC starts

**Solutions**:
- Verify device IP address and port are correct
- Check network connectivity: `ping <device-ip>`
- Ensure device is powered on and responding
- Check device documentation for correct protocol

### Slow Updates

**Problem**: PVs update slower than expected

**Solutions**:
- Check `update_period` in `io_ref` (lower = faster updates)
- Reduce number of attributes with fast updates
- Optimize device communication (batch queries if possible)
- Consider if device can handle higher query rate

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'p4p'` or similar

**Solutions**:
```bash
# Reinstall with extras
pip install --force-reinstall 'fastcs[ca,pva]'

# Or install individually
pip install pythonSoftIOC
pip install p4p
```

### GUI Not Generating

**Problem**: `.bob` file not created

**Solutions**:
- Check `output_path` is valid and writable
- Ensure directory exists (or will be created)
- Look for errors in IOC startup logs
- Verify `gui` parameter is passed to transport

## Best Practices

### PV Naming Conventions

```python
# Good: Clear, hierarchical names
MY-DEVICE:Temperature
MY-DEVICE:PowerSupply:Voltage
MY-DEVICE:Motor1:Position

# Avoid: Abbreviations, unclear names
MY-DEV:TEMP
MY-DEVICE:PSU1_V
MY-DEVICE:M1POS
```

### When to Use CA vs PVA

**Use both** when:
- Supporting legacy and modern clients
- During transition periods
- Maximum compatibility needed

**Use CA only** when:
- Only legacy clients exist
- Proven stability required
- Simple scalar values only

**Use PVA only** when:
- Only modern clients (Phoebus)
- Need structured data (Tables)
- Better performance required
- New deployment without legacy

### Performance Considerations

```python
# Good: Different update rates for different needs
class MyController(Controller):
    critical_temp: AttrR = AttrR(
        Float(),
        io_ref=IORef(command="TEMP", update_period=0.1)  # Fast: 10 Hz
    )

    device_id: AttrR = AttrR(
        String(),
        io_ref=IORef(command="ID", update_period=ONCE)  # Slow: 1/hour
    )
```

### Error Handling Patterns

```python
class RobustAttributeIO(AttributeIO):
    async def update(self, attr):
        try:
            response = await self._connection.send_query(
                f"{attr.io_ref.command}?\r\n",
                timeout=2.0
            )
            value = attr.dtype(response.strip())
            await attr.update(value)
        except asyncio.TimeoutError:
            # Log but don't crash - old value remains
            logger.warning(f"Timeout reading {attr.io_ref.command}")
        except ValueError as e:
            # Bad response format
            logger.error(f"Invalid response: {e}")
            raise  # Re-raise to stop updates
        except ConnectionError:
            # Connection lost - will try to reconnect
            logger.error("Device connection lost")
            raise
```

### Testing Strategies

```python
# Unit test example
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_temperature_update():
    # Mock connection
    mock_connection = AsyncMock()
    mock_connection.send_query.return_value = "23.5\r\n"

    # Create IO handler
    io = DeviceAttributeIO(mock_connection)

    # Create attribute
    attr = AttrR(Float(), io_ref=IORef(command="TEMP"))

    # Test update
    await io.update(attr)

    assert attr.get() == 23.5
    mock_connection.send_query.assert_called_once_with("TEMP?\r\n")
```

## Complete Working Example

Here's a complete, runnable example combining everything:

```python
"""
Complete FastCS IOC example with CA and PVA transports.
Simulates a temperature controller device.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW
from fastcs.connections import IPConnection, IPConnectionSettings
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Float, String
from fastcs.launch import FastCS
from fastcs.transports import (
    EpicsCATransport,
    EpicsPVATransport,
    EpicsGUIOptions,
    EpicsIOCOptions,
)

NumberT = TypeVar("NumberT", int, float)


@dataclass
class DeviceIORef(AttributeIORef):
    """Reference for device IO operations."""
    command: str
    update_period: float | None = 1.0


class DeviceIO(AttributeIO[NumberT, DeviceIORef]):
    """Handles device communication."""

    def __init__(self, connection: IPConnection):
        super().__init__()
        self._connection = connection

    async def update(self, attr):
        """Read from device."""
        response = await self._connection.send_query(
            f"{attr.io_ref.command}?\r\n"
        )
        value = attr.dtype(response.strip())
        await attr.update(value)

    async def send(self, attr):
        """Write to device."""
        await self._connection.send_command(
            f"{attr.io_ref.command}={attr.get()}\r\n"
        )


class TemperatureController(Controller):
    """Temperature controller with multiple attributes."""

    # Read-only attributes
    device_id: AttrR = AttrR(
        String(),
        io_ref=DeviceIORef(command="ID", update_period=10.0),
        description="Device serial number"
    )

    temperature: AttrR = AttrR(
        Float(),
        io_ref=DeviceIORef(command="TEMP", update_period=0.5),
        description="Current temperature in °C"
    )

    # Read-write attributes
    setpoint: AttrRW = AttrRW(
        Float(),
        io_ref=DeviceIORef(command="SETP", update_period=1.0),
        description="Temperature setpoint in °C"
    )

    enabled: AttrRW = AttrRW(
        Bool(),
        io_ref=DeviceIORef(command="ENABLE", update_period=1.0),
        description="Enable temperature control"
    )

    def __init__(self, host: str, port: int):
        """Initialize controller with device connection."""
        self._connection = IPConnection()
        self._settings = IPConnectionSettings(host, port)

        # Create IO handler
        device_io = DeviceIO(self._connection)

        super().__init__(ios=[device_io])

    async def connect(self):
        """Establish connection to device."""
        await self._connection.connect(self._settings)


def main():
    """Main entry point."""
    # Configure Channel Access transport
    ca_transport = EpicsCATransport(
        epicsca=EpicsIOCOptions(pv_prefix="TEMP-CTRL"),
        gui=EpicsGUIOptions(
            output_path=Path("./temp_ctrl_ca.bob"),
            title="Temperature Controller (CA)"
        )
    )

    # Configure PV Access transport
    pva_transport = EpicsPVATransport(
        epicspva=EpicsIOCOptions(pv_prefix="TEMP-CTRL"),
        gui=EpicsGUIOptions(
            output_path=Path("./temp_ctrl_pva.bob"),
            title="Temperature Controller (PVA)"
        )
    )

    # Create controller
    controller = TemperatureController(
        host="192.168.1.100",
        port=5000
    )

    # Launch FastCS with both transports
    fastcs = FastCS(controller, [ca_transport, pva_transport])
    fastcs.run()


if __name__ == "__main__":
    main()
```

**To run this example:**

```bash
# Save as temperature_ioc.py in your project's src directory
# Run using uv
uv run python temperature_ioc.py

# Or if using the devcontainer, just:
python temperature_ioc.py

# Test with CA
caget TEMP-CTRL:Temperature
caput TEMP-CTRL:Setpoint 25.0

# Test with PVA
pvget TEMP-CTRL:Temperature
pvput TEMP-CTRL:Setpoint 25.0

# Open generated GUIs in Phoebus
# File -> Open -> temp_ctrl_ca.bob (or temp_ctrl_pva.bob)
```

## Next Steps

Now that you have a working IOC with CA and PVA transports:

- **Learn about dynamic drivers**: See [](dynamic-drivers.md) for runtime device introspection
- **Explore other transports**: Add Tango, GraphQL, or REST alongside EPICS
- **Implement methods**: Use `@command` and `@scan` decorators for complex operations
- **Read the architecture explanation**: Understand how FastCS works under the hood
- **Study the API reference**: Explore all available datatypes and options

## See Also

- [](installation.md) - Detailed installation instructions
- [](static-drivers.md) - Step-by-step tutorial for creating drivers
- [](dynamic-drivers.md) - Runtime device introspection
- [API Reference](../_api/fastcs.rst) - Complete API documentation
- [FastCS GitHub](https://github.com/DiamondLightSource/FastCS) - Source code and examples
