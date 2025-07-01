# Creating a FastCS Driver

## Demo Simulation

Within FastCS there is a tickit simulation of a temperature controller. Clone the FastCS
repository and open it in VS Code. The simulation can be run with the 
`Temp Controller Sim` launch config by typing `Ctrl+P debug ` (note the trailing 
whitespace), selecting the launch config and pressing enter. The simulation will then
sit and wait for commands to be sent. When it receives commands, it will log them to the
console to show what it is doing.

:::{note}
FastCS must be installed with the `demo` extra for the demo simulator to run. This can
be done by running `pip install 'fastcs[demo]'`.
:::

This tutorial will walk through the steps of writing a device driver to control this
simulation.

## FastCS Controllers

The core of a FastCS device driver is the `Controller`. This class is used to implement
control of a device and instances can be loaded into a FastCS application to expose its
functionality.

Create a `TemperatureController` class that inherits from `Controller`.

::::{admonition} Code 1
:class: dropdown, hint

:::{literalinclude} /snippets/static01.py
:::

::::

## FastCS Launcher

The entrypoint to a FastCS application is the `FastCS` class. This takes a `Controller`
and a list of transports to expose the API through and provides a `run` method to launch
the application. Create a `FastCS` instance, pass the `TemperatureController` to it
along with an empty list of transports (for now).

::::{admonition} Code 2
:class: dropdown, hint

:::{literalinclude} /snippets/static02.py
:emphasize-lines: 2,9,10
:::

::::

Now the application runs, but it still doesn't expose any API because the `Controller`
is empty. It also completes immediately.

## FastCS Attributes

The simulator has an API to get its ID. To expose this in the driver, an `Attribute` can
be added to the `Controller`. There are 3 types of `Attribute`: `AttrR`, `AttrW` and
`AttrRW`, representing the access mode of the API. The ID can be read, but it cannot be
written, so add an `AttrR`. An `Attribute` also needs a type. The ID from the simulator
is a string, so `String` should be used.

::::{admonition} Code 3
:class: dropdown, hint

:::{literalinclude} /snippets/static03.py
:emphasize-lines: 1,3,8
:::

::::

Now the controller has a property that will appear in the API, but the application still
completes immediately because there are no transports being run on the event loop to
expose an API.

## FastCS Transports

FastCS supports multiple transports to expose the API of the loaded `Controller`. The
following transports are currently supported

- EPICS CA (using `pythonSoftIOC`)
- EPICS PVA (using `p4p`)
- Tango (using `pytango`)
- GraphQL (using `strawberry`)
- HTTP (using `fastapi`)

One or more of these can be loaded into the application and run in parallel. Add the
EPICS CA transport to the application by creating an `EPICSCAOptions` instance and
passing it in.

::::{admonition} Code 4
:class: dropdown, hint

:::{literalinclude} /snippets/static04.py
:emphasize-lines: 5,6,13,14
:::

::::

:::{warning}
In the above snippet and all hereafter, the final line is commented out. This is done to 
avoid blocking our unit tests - in your own code, it should remain uncommented.
:::

The application will now run until it is stopped. There will also be a `DEMO:DeviceId`
PV being served by the application. However, the record is unset because the
`Controller` is not yet querying the simulator for the value.

```bash
❯ caget -S DEMO:DeviceId
DEMO:DeviceId
```

Now that the controller has a PV, it would be useful to open a UI. Add EPICS GUI
options to the transport options and generate a `demo.bob` file to use with Phoebus.

::::{admonition} Code 5
:class: dropdown, hint

:::{literalinclude} /snippets/static05.py
:emphasize-lines: 1,7,15-21,24
:::

::::

The `demo.bob` will have been created in the directory the application was run from.

## FastCS Device Connection

The `Attributes` of a FastCS `Controller` need some IO with the device in order to get
and set values. This is implemented with handlers and connections. There are three types
of handler - `Sender`, `Updater` and `Handler` (which implements both). Generally each
driver implements its own connection logic, but there are some built in options.

Update the controller to create an `IPConnection` to communicate with the simulator over
TCP and implement a `connect` method that establishes the connection. The `connect`
method is called by the FastCS application at the appropriate time during start up to
ensure the connection is established before it is used.

:::{note}
The simulator control connection is on port 25565.
:::

::::{admonition} Code 6
:class: dropdown, hint

:::{literalinclude} /snippets/static06.py
:emphasize-lines: 4,15-22,32-33
:::

::::

:::{warning}
The application will now fail to connect if the demo simulation is not running.
:::

The `Controller` has now established a connection with the simulator. This connection
can be passed to an `Updater` to enable it to query the device API and update the value
in the `device_id` attribute. Create an `Updater` child class and implement the method
to send a query to the device and set the value of the attribute, and then pass an
instance of the `Updater` to the `device_id` attribute.

:::{note}
The `update_period` property tells the base class how often to call `update`
:::

::::{admonition} Code 7
:class: dropdown, hint

:::{literalinclude} /snippets/static07.py
:emphasize-lines: 1-3,6,8,15-35,39
:::

::::

:::{note}
In the `update` method, errors won't crash the application, but it prints them to the
terminal. - `Update loop ... stopped:`
:::

Now the PV will be set by reading from the simulator and the IOC has one fully
functional PV.

```bash
❯ caget -S DEMO:DeviceId
DEMO:DeviceId SIMTCONT123
```

## Building Up The API

The simulator supports many other commands, for example it reports the total power
currently being drawn with the `P` command. This can be exposed by adding another
`AttrR` with a `Float` datatype, but the `IDUpdater` only supports the `ID` command to
get the device ID. This new attribute could have its own updater, but it would be better
to create common updater that can be configured with the command to send so that they
can share the same code.

Modify the handler to take a `command_name` string and use it to create a new attribute
to read the power usage.

:::{note}
All responses from the `IPConnection` are strings. This is fine for the `ID` command
because the value is actually a string, but for `P` the value is a float, so the
`update` methods needs to explicitly cast to the correct type. It can use
`Attribute.dtype` to call the builtin for its datatype - e.g. `int`, `float`, `str`,
etc.
::::

:::{admonition} Code 8
:class: dropdown, hint

:::{literalinclude} /snippets/static08.py
:emphasize-lines: 9,16-17,33-35,38,42-43
:::

::::

Now the IOC has two PVs being polled periodically. The new PV will be visible in the
Phoebus UI on refresh (right-click). `DEMO:Power` will read as `0` because the simulator
is not currently running a ramp. To do that the controller needs to be able to set
values on the device, as well as read them back. The ramp rate of the temperature can be
read with the `R` command and set with the `R=...` command. This means the controller
also needs a `Sender` handler that implements `put` to send values to the device.

Update the existing handler to support both `update` and `put`, making it a `Handler`
(which implements both `Updater` and `Sender`). Then add a new `AttrRW` with type
`Float` to get and set the ramp rate.

:::{note}
The set commands do not return a response, so use the `send_command` method instead of
`send_query`.
:::

::::{admonition} Code 9
:class: dropdown, hint

:::{literalinclude} /snippets/static09.py
:emphasize-lines: 5,7,17,41-44, 48-50
:::

::::

Two new PVs will be created: one to set the ramp rate and one to read it back.

```bash
❯ caget DEMO:RampRate_RBV
DEMO:RampRate_RBV              2
❯ caput DEMO:RampRate 5
Old : DEMO:RampRate                  2
New : DEMO:RampRate                  5
❯ caget DEMO:RampRate_RBV
DEMO:RampRate_RBV              5
```

The changes will also be visible in the simulator terminal.

```
INFO:fastcs.demo.simulation.device:Set ramp rate to 5.0
```

This adds the first method to modify the device, but more are needed to be able to run a
temperature ramp. The simulator has multiple temperature control loops that can be
ramped independently. They each have a common set of commands that control them
individually, for example to `S01=...` to set the start point for ramp 1, `E02=...` to
set the end point for ramp 2.

Given that the device has `n` instances of a common interface, it makes sense to create
a class to encapsulate this control and then instantiate it for each ramp the simulator
has. This can be done with the use of sub controllers. Controllers can be arbitrarily
nested to match the structure of a device and this structure is then mirrored to the
transport layer for the visibility of the user.

Create a `TemperatureRampController` with `AttrRW`s to get and set the ramp start and
end, update the `TemperatureControllerHandler` to include an optional suffix for the
commands so that it can be shared between the parent `TemperatureController` and add an
argument to define how many ramps there are, which is used to register the correct
number of ramp controllers with the parent.

::::{admonition} Code 10
:class: dropdown, hint

:::{literalinclude} /snippets/static10.py
:emphasize-lines: 9,10,20,23,27,35,43,47-56,64,66,72-76,90
:::

::::

New PVs will be added (e.g. `DEMO:R1:Start`):
- `DEMO:R{1,2,3,4}:Start`
- `DEMO:R{1,2,3,4}:Start_RBV`
- `DEMO:R{1,2,3,4}:End`
- `DEMO:R{1,2,3,4}:End_RBV`

Four buttons will also be added to the Phoebus UI to open sub screens for each ramp.

This allows the controller to set the range of every temperature ramp. Again, the
simulator terminal will confirm that the changes are taking effect. The final commands
needed to run a temperature ramp are the `N01` and `N01=` commands, which are used to
enable (and disable) the ramping.

Add an `AttrRW` to the `TemperatureRampController`s with an `Enum` type, using a
`StrEnum` with states `Off` and `On`.

::::{admonition} Code 11
:class: dropdown, hint

:::{literalinclude} /snippets/static11.py
:emphasize-lines: 3,11,48-50,56
:::

::::

Now the temperature ramp can be run.

```bash
❯ caput DEMO:R1:Enabled On
Old : DEMO:R1:Enabled                Off
New : DEMO:R1:Enabled                On
❯ caget DEMO:Power
DEMO:Power                     56.84
❯ caput DEMO:R1:Enabled Off
Old : DEMO:R1:Enabled                On
New : DEMO:R1:Enabled                Off
❯ caget DEMO:Power
DEMO:Power                     0
```

In the simulator terminal the progress of the ramp can be seen as it happens.

```
INFO:fastcs.demo.simulation.device:Started ramp 0
INFO:fastcs.demo.simulation.device:Target Temperatures: 10.000, 0.000, 0.000, 0.000
INFO:fastcs.demo.simulation.device:Actual Temperatures: 9.572, 0.000, 0.000, 0.000
INFO:fastcs.demo.simulation.device:Target Temperatures: 10.200, 0.000, 0.000, 0.000
INFO:fastcs.demo.simulation.device:Actual Temperatures: 9.952, 0.000, 0.000, 0.000
INFO:fastcs.demo.simulation.device:Target Temperatures: 10.400, 0.000, 0.000, 0.000
...
INFO:fastcs.demo.simulation.device:Stopped ramp 0
```

The target and actual temperatures visible in the simulator terminal are also exposed in
the API with the `T01?` and `A01?` commands.

## FastCS Methods

The applied voltage for each ramp is also available with the `V?` command, but the value
is an array with each element corresponding to a ramp. Here it will be simplest to
manually fetch the array in the parent controller and pass each value into ramp
controller. This can be done with a `scan` method - these are called at a defined rate,
similar to the `update` method of handlers.

Add an `AttrR` for the voltage to the `TemperatureRampController`, but do not pass it a
handler. Then add a method to the `TemperatureController` with a `@scan` decorator that
gets the array of voltages and sets each ramp controller with its value. Also add
`AttrR`s for the target and actual temperature for each ramp as described above.

::::{admonition} Code 12
:class: dropdown, hint

:::{literalinclude} /snippets/static12.py
:emphasize-lines: 4,16,59-61,93-99
:::

::::

Creating attributes is intended to be a simple API covering most use cases, but where
more flexibility is needed wrapped controller methods can be useful to avoid adding
complexity to the handlers to handle a small subset of attributes. It is also useful for
implementing higher level logic on top of the attributes that expose the API of a device
directly. For example, it would be useful to have a single button to stop all of the
ramps at the same time. This can be done with a `command` method. These are similar to
`scan` methods except that they create an API in transport layer in the same way an
attribute does.

Add a method with a `@command` decorator to set enabled to false in every ramp
controller.

::::{admonition} Code 13
:class: dropdown, hint

:::{literalinclude} /snippets/static13.py
:emphasize-lines: 3,17,102-108
:::

::::

The new `DEMO:CancelAll` PV can be set (the value doesn't matter) to stop all of the
ramps.

```
❯ caget DEMO:R1:Enabled_RBV
DEMO:R1:Enabled_RBV            On
❯ caput DEMO:DisableAll 1
Old : DEMO:DisableAll
New : DEMO:DisableAll
❯ caget DEMO:R1:Enabled_RBV
DEMO:R1:Enabled_RBV            Off
```

## Summary

This demonstrates some of the simple use cases for a statically defined FastCS driver.
It is also possible to instantiate a driver dynamically by instantiating a device during
startup. See the next tutorial for how to do this (TODO).
