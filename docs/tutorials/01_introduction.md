# Tutorial 1: Introduction to DRS

Welcome to the **Discrete Rate Simulation (DRS)** framework! This step-by-step guide will walk you through the core concepts, from defining variables to running a basic simulation.

You can find the runnable Python code for this tutorial in [01_getting_started.py](file:///Users/jonathanlamontange-kratz/Documents/GitHub/mining-drs/examples/tutorial/01_getting_started.py).

---

## 1. Core Types

At the heart of the framework are three primary state container types: `Variable`, `Level`, and `Timer`.

- **`Variable`**: Holds a named value that changes discretely (e.g., an extraction rate target or operation status).
- **`Level`**: A specialized variable that accumulates continuous quantity over time using a rate (like an integral over time). Only `Level` has a `.rate` attribute; attempting to set or get a rate on a plain `Variable` will fail fast with an error.
- **`Timer`**: A specialized `Level` that automatically ticks forward at a rate of `1.0` by default. It is useful for tracking elapsed simulation time or setting event countdowns.

Here is how you initialize them:

```python
import drs

# Variables hold named state. They are owned by whatever Module creates them.
rate = drs.Variable("extraction_rate", 5000.0)
print(f"Variable value: {rate.value} t/day")

# Levels accumulate over time using a rate (like an integral in dt).
stockpile = drs.Level("ore_stockpile", initial_value=0.0)
stockpile.rate = 5000.0
print(f"Level rate: {stockpile.rate} t/day")

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

Here, we define a physical `Stockpile` and a `Mill`:

```python
class Stockpile(drs.Module):
    """A stockpile that receives ore and feeds a mill."""

    def __init__(self, name: str, initial_mass: float = 0.0):
        super().__init__()
        self.mass = drs.Level(f"{name}_mass", initial_value=initial_mass)
        self.outflow = drs.Variable(f"{name}_outflow", 0.0)

    def forward(self, inflow_rate: Flow, requested_outflow: Variable):
        # Determine actual outflow based on what is physically available in the stockpile
        outflow = min(requested_outflow.value, self.mass.value) if self.mass.value > 0 else 0.0
        
        # Physics update: rate of accumulation is inflow minus outflow
        self.mass.rate = inflow_rate.value - outflow
        self.outflow.value = outflow
        return Flow(outflow)


class Mill(drs.Module):
    """A mill that consumes ore from a stockpile."""

    def __init__(self, name: str, max_rate: float):
        super().__init__()
        self.name = name
        self.max_rate = drs.Variable(f"{name}_max_rate", max_rate)
        self.total_milled = drs.Level(f"{name}_total_milled", initial_value=0.0)
        self.feed_rate = drs.Variable(f"{name}_feed_rate", 0.0)

    def forward(self, available: Flow):
        # Mill operates at either the maximum capacity or the available feed rate
        actual = min(available.value, self.max_rate.value)
        self.total_milled.rate = actual
        self.feed_rate.value = actual

```

---

## 3. Wiring It Together

You compose nested module hierarchies by assigning sub-modules as attributes of a parent module. 
When a module reads a variable owned by another module, or returns a flow rate that is passed to another, the framework **automatically records this as a dependency edge**, implicitly building the simulation's dependency graph.

To ensure safety, any physical quantity flowing between modules must be wrapped in a `drs.Flow` object.

```python
from drs import Flow

class SimpleMine(drs.Module):
    """A complete mini simulation: mine → stockpile → mill."""

    def __init__(self):
        super().__init__()
        self.stockpile = Stockpile("ore", initial_mass=100.0)
        self.mill = Mill("concentrator", max_rate=6000.0)
        self.extraction_rate = drs.Variable("mine_rate", 8000.0)

    def forward(self):
        # 1. Wrap extraction rate in a Flow
        inflow = Flow(self.extraction_rate.value)
        
        # 2. Call stockpile with inflow and the mill's max_rate Variable
        available_outflow = self.stockpile(inflow, self.mill.max_rate)
        
        # 3. Feed the mill with the available outflow Flow
        self.mill(available_outflow)
```

---

## 4. Running the Engine

With your model built, pass it to the `DRSEngine` to execute the simulation. The engine handles zeroing out rates, calling the model's `forward()` pass, finding event boundaries, and integrating the states forward.

```python
from drs.engine import DRSEngine

# 1. Instantiate the model
model = SimpleMine()

# 2. Give it to the engine
engine = DRSEngine(model, max_step_size=0.5)

# 3. Run for 10 simulated days
result = engine.run(max_time=10.0)

# 4. Check the results
print(result.summary())
print(f"Stockpile mass: {model.stockpile.mass.value:.1f} t")
print(f"Mill total milled: {model.mill.total_milled.value:.1f} t")
```

Now that you've got the basics down, head over to [Tutorial 2: Advanced Core Dynamics & Guardrails](02_advanced_dynamics.md) to see how the engine manages event thresholds and enforces strict physical safety rules!
