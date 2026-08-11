# Tutorial 6: Operating Modes & Controllers

In large-scale continuous flow systems, you often need to adjust routing splits, feeding rates, or production levels based on the state of the network. For instance, if a primary stockpile gets too low, you might trigger a "surging" mode to replenish it. If it gets too full, you might throttle production.

This tutorial covers the standard design patterns in Mining-DRS for managing **Operating Modes** and structuring **Controller Modules**.

You can find the runnable Python code for this tutorial in [06_operating_modes.py](file:///Users/jonathanlamontange-kratz/Documents/GitHub/mining-drs/examples/tutorial/06_operating_modes.py).

---

## 1. Clean Architectural Separation

When building a simulator, always separate your components into two distinct layers:
1. **Physical Layer**: Modules that represent physical equipment and constraints (e.g., Stockpiles, Conveyors, Mills, Trucks). They own physical state (`Level` variables) and do not make high-level decisions.
2. **Decision Layer (Controllers)**: Modules that read physical states, evaluate thresholds, manage the "operating mode" state, and assign target rates or routing coefficients to the physical layer.

---

## 2. Implementing a Mode Controller

Here is a design pattern for a clean, state-dependent controller that switches between **NORMAL**, **CONTINGENCY**, and **SHUTDOWN** modes based on a buffer stockpile level.

### Step 1: The Physical Components

First, we define a simple stockpile and mill:

```python
import drs
from drs import Module, Level, Variable

class PhysicalStockpile(Module):
    def __init__(self):
        super().__init__()
        self.mass = Level("mass", initial_value=250.0)

    def forward(self, inflow: Variable, outflow: Variable):
        # Accumulate or drain stockpile mass based on rates set by the controller
        self.mass.rate = inflow.value - outflow.value


class PhysicalMill(Module):
    def __init__(self):
        super().__init__()
        self.total_milled = Level("total_milled", initial_value=0.0)

    def forward(self, feed_rate: Variable):
        self.total_milled.rate = feed_rate.value
```

### Step 2: The Mode Controller

The controller reads the stockpile level and decides:
- If stockpile mass > 400: Switch to **NORMAL** (mill operates at 100 t/h).
- If stockpile mass falls below 100: Switch to **CONTINGENCY** (reduce mill rate to 40 t/h to avoid stockouts).
- If stockpile mass falls below 10: Switch to **SHUTDOWN** (turn mill off).

```python
class BlendingController(Module):
    def __init__(self, stockpile: PhysicalStockpile, mill: PhysicalMill):
        super().__init__()
        self.stockpile = stockpile
        self.mill = mill
        
        # State variable to track the active decision mode
        self.active_mode = Variable("mode", "NORMAL")
        
        # Output decision variables
        self.mine_target = Variable("mine_target", 80.0)
        self.mill_target = Variable("mill_target", 100.0)

    def forward(self):
        # 1. Read physical state (reads recorded as dependencies)
        pile_mass = self.stockpile.mass.value
        current_mode = self.active_mode.value

        # 2. Evaluate state transitions and change active mode (using epsilons for threshold detection)
        if current_mode == "NORMAL":
            if pile_mass <= 100.0 + 1e-6:
                self.active_mode.value = "CONTINGENCY"
                print(f"[CONTROLLER] t={self.current_time():.2f}: Stockpile low ({pile_mass:.1f}t). Switching to CONTINGENCY.")
        elif current_mode == "CONTINGENCY":
            if pile_mass >= 200.0 - 1e-6:
                self.active_mode.value = "NORMAL"
                print(f"[CONTROLLER] t={self.current_time():.2f}: Stockpile recovered ({pile_mass:.1f}t). Returning to NORMAL.")
            elif pile_mass <= 10.0 + 1e-6:
                self.active_mode.value = "SHUTDOWN"
                print(f"[CONTROLLER] t={self.current_time():.2f}: Stockpile critically empty ({pile_mass:.1f}t). Switching to SHUTDOWN.")
        elif current_mode == "SHUTDOWN":
            if pile_mass >= 150.0 - 1e-6:
                self.active_mode.value = "CONTINGENCY"
                print(f"[CONTROLLER] t={self.current_time():.2f}: Stockpile partially recovered ({pile_mass:.1f}t). Switching to CONTINGENCY.")

        # 3. Apply target dynamics based on active mode
        if self.active_mode.value == "NORMAL":
            self.mine_target.value = 80.0
            self.mill_target.value = 100.0
        elif self.active_mode.value == "CONTINGENCY":
            self.mine_target.value = 100.0 # surge mining
            self.mill_target.value = 40.0  # throttle milling
        elif self.active_mode.value == "SHUTDOWN":
            self.mine_target.value = 100.0
            self.mill_target.value = 0.0   # shutdown milling

        # 4. Bind thresholds to stockpiles to trigger re-evaluations
        if self.active_mode.value == "NORMAL":
            self.stockpile.mass.lower_threshold = 100.0
            self.stockpile.mass.upper_threshold = 500.0
        elif self.active_mode.value == "CONTINGENCY":
            self.stockpile.mass.lower_threshold = 10.0
            self.stockpile.mass.upper_threshold = 200.0
        elif self.active_mode.value == "SHUTDOWN":
            self.stockpile.mass.lower_threshold = -drs.math.inf
            self.stockpile.mass.upper_threshold = 150.0
```

### Step 3: Integrating the Top-Level System

Finally, we group all child modules under a parent class and execute the `forward` pass to route data:

```python
class MiningSystem(Module):
    def __init__(self):
        super().__init__()
        self.stockpile = PhysicalStockpile()
        self.mill = PhysicalMill()
        self.controller = BlendingController(self.stockpile, self.mill)

    def forward(self):
        # 1. Run the controller first to update mode and routing decisions
        self.controller()
        
        # 2. Propagate targets to physical components (pass the Variable objects themselves!)
        self.stockpile(self.controller.mine_target, self.controller.mill_target)
        self.mill(self.controller.mill_target)
```

## 3. Running the Mode Simulation

We can run this system, and because of the threshold-driven design, the engine will step forward exactly to the moments where stockpile levels cross critical bounds, triggering clean mode switches:

```python
from drs.engine import DRSEngine
from drs.telemetry import Telemetry

model = MiningSystem()
engine = DRSEngine(model)
telemetry = Telemetry(model)
engine.attach_telemetry(telemetry)

# Run for 20 simulated hours
result = engine.run(max_time=20.0)
print(result.summary())
```

By applying this structural separation and using event-driven thresholds to drive your mode switches, your simulations will remain robust, clean, and highly performant.

Congratulations, you have completed all tutorials for the Mining-DRS framework!
