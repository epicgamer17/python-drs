# Tutorial 2: Advanced Core Dynamics & Guardrails

This tutorial dives under the hood of the Mining-DRS engine to explain how it achieves high performance through event-driven "time jumping" and how it protects your simulations from bugs using strict structural guardrails.

You can find the runnable Python code for this tutorial in [02_advanced_dynamics.py](file:///Users/jonathanlamontange-kratz/Documents/GitHub/mining-drs/examples/tutorial/02_advanced_dynamics.py).

---

## 1. How Event-Driven Time Jumping Works

Unlike traditional **fixed-step simulations** (which step forward by a set interval like every second, minute, or day), a **Discrete Rate Simulation (DRS)** steps forward dynamically based on events. 

In Mining-DRS, these events are defined by setting **thresholds** on `Level` variables.
- `Level.upper_threshold`: A maximum boundary (defaults to `math.inf`).
- `Level.lower_threshold`: A minimum boundary (defaults to `-math.inf`).

Every step, the engine calculates the time delta ($dt$) to the next event for each variable using current rates:
- If a level is filling up ($\text{rate} > 0$): 
  $$dt = \frac{\text{upper\_threshold} - \text{value}}{\text{rate}}$$
- If a level is emptying ($\text{rate} < 0$): 
  $$dt = \frac{\text{value} - \text{lower\_threshold}}{|\text{rate}|}$$

The engine finds the smallest positive $dt$ across all variables, jumps the simulation clock forward by exactly that amount, and applies integration to all levels:
$$\text{new\_value} = \text{value} + \text{rate} \times dt$$

### Example: Fills then Empties (Batch Processing)

Here is a module that utilizes thresholds to cycle between filling and emptying:

```python
import drs

class BatchTank(drs.Module):
    def __init__(self):
        super().__init__()
        self.tank = drs.Level("tank_level", initial_value=0.0)
        self.cycle_count = drs.Variable("cycles", 0)
        self._filling = True

    def forward(self):
        if self._filling:
            # Set rate and upper threshold
            self.tank.rate = (10.0, -drs.math.inf, 100.0) # (rate, lower, upper)
            
            # Switch to emptying when full
            if self.tank.value >= 100.0 - 1e-6:
                self._filling = False
                self.cycle_count.value += 1
        else:
            # Set rate and lower threshold
            self.tank.rate = (-5.0, 0.0, drs.math.inf)
            
            # Switch to filling when empty
            if self.tank.value <= 1e-6:
                self._filling = True
```

---

## 2. Structural Guardrails

To prevent silent physical bugs (like creating mass out of thin air or conflicting rate assignments), the engine enforces three strict guardrails.

### Guardrail 1: The Rule of Ownership (Cross-Module Mutation)

A module is only allowed to mutate variables that it **owns** (i.e., variables assigned as attributes to itself or its child modules). If a module attempts to write to a variable owned by another module during `forward()`, the engine detects this and raises a `StateMutationError`.

```python
class BadActor(drs.Module):
    def __init__(self, external_stockpile):
        super().__init__()
        self.external_stockpile = external_stockpile

    def forward(self):
        # ILLEGAL: This will raise StateMutationError!
        # You cannot directly modify variables owned by another module.
        self.external_stockpile.mass.value = 1000.0
```

> [!TIP]
> **Why?** Enforcing ownership ensures that all communication occurs through explicit arguments (`Flow` objects) and keeps the simulation graph traceable.

### Guardrail 2: Rate Conflict Protection

Multiple modules are not allowed to set the rate of the same `Level` during the same step. If a level's rate has already been assigned by one module, and another module tries to overwrite it, the engine raises a `StateMutationError`.

```python
class ConflictingModule(drs.Module):
    def __init__(self, shared_level):
        super().__init__()
        self.shared_level = shared_level

    def forward(self):
        # Setting this rate might conflict if another module already set it!
        self.shared_level.rate = 50.0
```

### Guardrail 3: Orphaned Threshold Check

If you configure a threshold on a `Level` but its rate is `0.0`, the threshold will never be reached, and the simulation might hang or ignore important logic. By default, the engine prints a warning about orphaned thresholds. 

If you enable **strict mode**, the engine will raise a `ThresholdConfigurationError` instead of warning.

```python
from drs.config import EngineConfig
from drs.engine import DRSEngine

config = EngineConfig(strict_mode=True)
engine = DRSEngine(model, config=config)
```

Now you know how the engine drives state transitions safely and efficiently. Move on to [Tutorial 3: Streaming Inputs & Data Sources](03_data_streams.md) to learn how to feed external data streams into your models.
