# Tutorial 6: Operating Modes & Controllers

In large-scale continuous flow systems, you often need to adjust routing splits, feeding rates, or production levels based on the state of the network. For instance, if a buffer tank gets too low, you might trigger a "surging" mode to replenish it. If it gets too full, you might throttle production.

This tutorial covers the standard design patterns in python-drs for managing **Operating Modes** and structuring **Controller Modules**.

---

## 1. Clean Architectural Separation

When building a simulator, always separate your components into two distinct layers:
1. **Physical Layer**: Modules that represent physical equipment and constraints (e.g., Tanks, Mixers, Pumps). They own physical state (`Level` variables) and do not make high-level decisions.
2. **Decision Layer (Controllers)**: Modules that read physical states, evaluate thresholds, manage the "operating mode" state, and assign target rates or routing coefficients to the physical layer.

---

## 2. Implementing a Mode Controller

Here is a design pattern for a clean, state-dependent controller that switches between **NORMAL**, **CONTINGENCY**, and **SHUTDOWN** modes based on a buffer tank level.

### Step 1: The Physical Components

First, we define a simple buffer tank and processor:

```python
import math
import drs
from drs import Module, Level, Variable

class PhysicalTank(Module):
    def __init__(self):
        super().__init__()
        self.volume = Level("buffer_volume", initial_value=250.0)

    def forward(self, inflow: Variable, outflow: Variable):
        # Accumulate or drain tank volume based on rates set by the controller
        self.volume.rate = inflow.value - outflow.value


class PhysicalProcessor(Module):
    def __init__(self):
        super().__init__()
        self.processed = Level("total_processed", initial_value=0.0)

    def forward(self, feed_rate: Variable):
        self.processed.rate = feed_rate.value
```

### Step 2: The Mode Controller

The controller reads the buffer level and decides:
- If buffer level > 400: Switch to **NORMAL** (processor operates at 100 units/h).
- If buffer level falls below 100: Switch to **CONTINGENCY** (reduce the processing rate to 40 units/h to avoid emptying the buffer).
- If buffer level falls below 10: Switch to **SHUTDOWN** (turn the processor off).

```python
class BufferController(Module):
    def __init__(self, tank: PhysicalTank, processor: PhysicalProcessor):
        super().__init__()
        self.tank = tank
        self.processor = processor

        # State variable to track the active decision mode
        self.active_mode = Variable("mode", "NORMAL")

        # Output decision variables
        self.production_target = Variable("production_target", 80.0)
        self.consumption_target = Variable("consumption_target", 100.0)

    def forward(self):
        # 1. Read physical state (reads recorded as dependencies)
        level = self.tank.volume.value
        current_mode = self.active_mode.value

        # 2. Evaluate state transitions and change active mode (using epsilons for threshold detection)
        if current_mode == "NORMAL":
            if level <= 100.0 + 1e-6:
                self.active_mode.value = "CONTINGENCY"
                print(f"[CONTROLLER] Buffer low ({level:.1f}). Switching to CONTINGENCY.")
        elif current_mode == "CONTINGENCY":
            if level >= 200.0 - 1e-6:
                self.active_mode.value = "NORMAL"
                print(f"[CONTROLLER] Buffer recovered ({level:.1f}). Returning to NORMAL.")
            elif level <= 10.0 + 1e-6:
                self.active_mode.value = "SHUTDOWN"
                print(f"[CONTROLLER] Buffer critically empty ({level:.1f}). Switching to SHUTDOWN.")
        elif current_mode == "SHUTDOWN":
            if level >= 150.0 - 1e-6:
                self.active_mode.value = "CONTINGENCY"
                print(f"[CONTROLLER] Buffer partially recovered ({level:.1f}). Switching to CONTINGENCY.")

        # 3. Apply target dynamics based on active mode
        if self.active_mode.value == "NORMAL":
            self.production_target.value = 80.0
            self.consumption_target.value = 100.0
        elif self.active_mode.value == "CONTINGENCY":
            self.production_target.value = 100.0  # surge production
            self.consumption_target.value = 40.0   # throttle processing
        elif self.active_mode.value == "SHUTDOWN":
            self.production_target.value = 100.0
            self.consumption_target.value = 0.0    # processor off

        # 4. Bind thresholds to the tank to trigger re-evaluations
        if self.active_mode.value == "NORMAL":
            self.tank.volume.lower_threshold = 100.0
            self.tank.volume.upper_threshold = 500.0
        elif self.active_mode.value == "CONTINGENCY":
            self.tank.volume.lower_threshold = 10.0
            self.tank.volume.upper_threshold = 200.0
        elif self.active_mode.value == "SHUTDOWN":
            self.tank.volume.lower_threshold = -math.inf
            self.tank.volume.upper_threshold = 150.0
```

### Step 3: Integrating the Top-Level System

Finally, we group all child modules under a parent class and execute the `forward` pass to route data:

```python
class ProductionSystem(Module):
    def __init__(self):
        super().__init__()
        self.tank = PhysicalTank()
        self.processor = PhysicalProcessor()
        self.controller = BufferController(self.tank, self.processor)

    def forward(self):
        # 1. Run the controller first to update mode and routing decisions
        self.controller()

        # 2. Propagate targets to physical components (pass the Variable objects themselves!)
        self.tank(self.controller.production_target, self.controller.consumption_target)
        self.processor(self.controller.consumption_target)
```

---

## 3. Running the Mode Simulation

We can run this system, and because of the threshold-driven design, the engine will step forward exactly to the moments where buffer levels cross critical bounds, triggering clean mode switches:

```python
from drs.engine import DRSEngine
from drs.telemetry import Telemetry

model = ProductionSystem()
engine = DRSEngine(model)
telemetry = Telemetry(model)
engine.attach_telemetry(telemetry)

# Run for 20 simulated time units
result = engine.run(max_time=20.0)
print(result.summary())
```

By applying this structural separation and using event-driven thresholds to drive your mode switches, your simulations will remain robust, clean, and highly performant.

Congratulations, you have completed all tutorials for the python-drs framework!