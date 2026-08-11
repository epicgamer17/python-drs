# Tutorial 1: Introduction to DRS

Welcome to the **Discrete Rate Simulation (DRS)** framework! This step-by-step guide will walk you through the core concepts, from defining variables to running a basic simulation.

---

## 1. Core Types

At the heart of the framework are three primary state container types: `Variable`, `Level`, and `Timer`.

- **`Variable`**: Holds a named value that changes discretely (e.g., a rate target or an operation status).
- **`Level`**: A specialized variable that accumulates continuous quantity over time using a rate (like an integral over time). Only `Level` has a `.rate` attribute; attempting to set or get a rate on a plain `Variable` will fail fast with an error.
- **`Timer`**: A specialized `Level` that automatically ticks forward at a rate of `1.0` by default. It is useful for tracking elapsed simulation time or setting event countdowns.

Here is how you initialize them:

```python
import drs

# Variables hold named state. They are owned by whatever Module creates them.
rate = drs.Variable("inflow_rate", 50.0)
print(f"Variable value: {rate.value} units/day")

# Levels accumulate over time using a rate (like an integral in dt).
tank = drs.Level("tank_volume", initial_value=0.0)
tank.rate = 50.0
print(f"Level rate: {tank.rate} units/day")

# Timers are Levels that tick at rate=1.0 by default.
clock = drs.Timer("elapsed_days", initial_value=0.0)
print(f"Timer initial value: {clock.value}")
```

---

## 2. Defining Modules

A `Module` is the fundamental building block of your simulation, heavily inspired by `nn.Module` in PyTorch. A module:
1. Inherits from `drs.Module`.
2. Registers any child modules or variables assigned as attributes during `__init__`.
3. Defines its dynamics and physical formulas in a `forward()` pass.

Here, we define a physical `StorageTank` and a `Processor`:

```python
from drs import Flow

class StorageTank(drs.Module):
    """A tank that receives inflow and services a downstream processor."""

    def __init__(self, name: str, initial_volume: float = 0.0):
        super().__init__()
        self.volume = drs.Level(f"{name}_volume", initial_value=initial_volume)
        self.outflow = drs.Variable(f"{name}_outflow", 0.0)

    def forward(self, inflow_rate: Flow, requested_outflow: drs.Variable):
        # Determine actual outflow based on what is physically available in the tank
        outflow = min(requested_outflow.value, self.volume.value) if self.volume.value > 0 else 0.0

        # Physics update: rate of accumulation is inflow minus outflow
        self.volume.rate = inflow_rate.value - outflow
        self.outflow.value = outflow
        return Flow(outflow)


class Processor(drs.Module):
    """A processor that consumes fluid from a storage tank."""

    def __init__(self, name: str, max_rate: float):
        super().__init__()
        self.name = name
        self.max_rate = drs.Variable(f"{name}_max_rate", max_rate)
        self.processed = drs.Level(f"{name}_processed", initial_value=0.0)
        self.feed_rate = drs.Variable(f"{name}_feed_rate", 0.0)

    def forward(self, available: Flow):
        # Process at either the maximum capacity or the available feed rate
        actual = min(available.value, self.max_rate.value)
        self.processed.rate = actual
        self.feed_rate.value = actual

```

---

## 3. Wiring It Together

You compose nested module hierarchies by assigning sub-modules as attributes of a parent module.
When a module reads a variable owned by another module, or returns a flow rate that is passed to another, the framework **automatically records this as a dependency edge**, implicitly building the simulation's dependency graph.

To ensure safety, any physical quantity flowing between modules must be wrapped in a `drs.Flow` object.

```python
from drs import Flow

class FluidNetwork(drs.Module):
    """A complete mini simulation: inflow → tank → processor."""

    def __init__(self):
        super().__init__()
        self.tank = StorageTank("buffer", initial_volume=100.0)
        self.processor = Processor("processor", max_rate=60.0)
        self.inflow_rate = drs.Variable("inflow_rate", 80.0)

    def forward(self):
        # 1. Wrap the inflow rate in a Flow
        inflow = Flow(self.inflow_rate.value)

        # 2. Call the tank with the inflow and the processor's max_rate Variable
        available_outflow = self.tank(inflow, self.processor.max_rate)

        # 3. Feed the processor with the available outflow Flow
        self.processor(available_outflow)
```

---

## 4. Running the Engine

With your model built, pass it to the `DRSEngine` to execute the simulation. The engine handles zeroing out rates, calling the model's `forward()` pass, finding event boundaries, and integrating the states forward.

```python
from drs.engine import DRSEngine

# 1. Instantiate the model
model = FluidNetwork()

# 2. Give it to the engine
engine = DRSEngine(model, max_step_size=0.5)

# 3. Run for 10 simulated time units
result = engine.run(max_time=10.0)

# 4. Check the results
print(result.summary())
print(f"Tank volume: {model.tank.volume.value:.1f}")
print(f"Processor total processed: {model.processor.processed.value:.1f}")
```

Now that you've got the basics down, head over to [Tutorial 2: Advanced Core Dynamics & Guardrails](02_advanced_dynamics.md) to see how the engine manages event thresholds and enforces strict physical safety rules!