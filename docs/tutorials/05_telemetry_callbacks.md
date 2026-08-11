# Tutorial 5: Telemetry & Custom Callbacks

To build production-ready simulators, you need a way to monitor the internal states of your modules, track custom performance metrics (such as operating costs, throughput, or efficiency), and hook custom code into the simulation lifecycle. 

This tutorial covers the two main monitoring APIs in Mining-DRS: **Telemetry** and **Callbacks**.

You can find the runnable Python code for this tutorial in [05_telemetry_callbacks.py](file:///Users/jonathanlamontange-kratz/Documents/GitHub/mining-drs/examples/tutorial/05_telemetry_callbacks.py).

---

## 1. The Telemetry System

The `Telemetry` class records variable snapshots at every simulation step and allows you to calculate custom derived metrics.

### Tracking Variables and Custom Metrics

```python
import drs
from drs import Module, Level, Variable
from drs.telemetry import Telemetry
from drs.engine import DRSEngine

class GrindingMill(Module):
    def __init__(self):
        super().__init__()
        self.ore = Level("ore_milled", initial_value=0.0)
        self.power_draw = Variable("power_draw_kw", 450.0) # constant power consumption

    def forward(self):
        # Stop milling if we have reached our target of 500 tons
        if self.ore.value >= 500.0 - 1e-6:
            self.ore.rate = 0.0
        else:
            self.ore.rate = 100.0
            self.ore.upper_threshold = 500.0

# 1. Setup model, engine, and telemetry
model = GrindingMill()
engine = DRSEngine(model)
telemetry = Telemetry(model)
engine.attach_telemetry(telemetry)

# 2. Register a custom derived metric
# Signature: calc_fn(current_time, model, state, history) -> float
def calc_energy_efficiency(t, mod, state, history):
    # Calculate cumulative energy (kWh) divided by tons milled
    milled_tons = mod.ore.value
    power = mod.power_draw.value
    total_energy_kwh = power * t
    return total_energy_kwh / milled_tons if milled_tons > 0 else 0.0

telemetry.register_metric("kwh_per_ton", calc_energy_efficiency)

# 3. Run the engine
engine.run(max_time=10.0)

# 4. Extract telemetry records as a pandas DataFrame
df = telemetry.to_dataframe()
print(df[["time", "ore_milled", "kwh_per_ton"]].head())
```

### Live Snapshots

If you are building a live dashboard or writing real-time logs, pass a callback to the `on_snapshot` argument of `Telemetry`. This function runs every time a step snapshot is captured:

```python
def stream_to_console(state_snapshot):
    print(f"Live Snapshot: t={state_snapshot['time']:.2f} | Ore={state_snapshot['ore_milled']:.1f}")

telemetry = Telemetry(model, on_snapshot=stream_to_console)
```

---

## 2. Using Custom Callbacks

While `Telemetry` focuses on tracking data, the `Callback` class allows you to execute custom logic at key lifecycle stages of the simulation.

To create a callback, subclass `drs.callbacks.Callback` and override any of these hooks:
- `on_simulation_start(self, engine)`: Runs before the simulation loop begins.
- `on_step_start(self, engine)`: Runs at the beginning of each simulation step, after rates are zeroed.
- `on_threshold(self, engine, trigger_var, is_upper)`: Runs when a level hits a threshold.
- `on_deadlock(self, engine)`: Runs immediately before a `DeadlockError` is raised.
- `on_complete(self, engine, result)`: Runs after the simulation completely finishes.

### Example: Custom Event Logger

Here is a callback that prints to the console whenever a variable threshold is hit:

```python
from drs.callbacks import Callback

class ThresholdLoggerCallback(Callback):
    def on_threshold(self, engine, trigger_var, is_upper):
        direction = "upper" if is_upper else "lower"
        threshold = trigger_var.upper_threshold if is_upper else trigger_var.lower_threshold
        print(f"[CALLBACK] t={engine.current_time:.2f}: '{trigger_var.name}' hit {direction} threshold of {threshold}!")

# Register the callback with the engine
logger_callback = ThresholdLoggerCallback()
engine = DRSEngine(model, callbacks=[logger_callback])
```

---

## 3. Built-in Progress Bar Callback

Mining-DRS includes a built-in progress bar callback that uses the `rich` library to show a visual CLI progress bar during execution.

To enable it, set `progress_bar=True` when initializing `DRSEngine`:

```python
# Enables the ProgressBarCallback under the hood
engine = DRSEngine(model, progress_bar=True)
engine.run(max_time=100.0)
```

Now you know how to observe your simulation runs and tap into the engine's execution loops. Move on to [Tutorial 6: Design Patterns: Operating Modes](06_operating_modes.md) to explore common design patterns for advanced simulation routing.
