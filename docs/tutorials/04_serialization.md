# Tutorial 4: Checkpointing & State Serialization

python-drs provides robust systems to save, load, and inspect the state of your models and the simulation engine.

These capabilities allow you to:
1. **Save/Load Weights/State**: Save and reload the values of all variables in a module tree, exactly like PyTorch's `state_dict()` and `load_state_dict()`.
2. **Export Architecture**: Export the structural schema of your modules to a JSON format (useful for drawing graphs or configuration files).
3. **Full Simulation Checkpointing**: Capture a complete snapshot of the `DRSEngine` (including current time, step count, RNG states, event logs, and all variables/rates) to support branching scenarios or mid-run rewinding.

---

## 1. Module State Dict and Architecture

### Saving and Loading Variable Values

You can capture and restore the state of all variables using `state_dict()` and `load_state_dict()`, or write them directly to/from a file with `save_state` and `load_state`:

```python
import drs
from drs.serialize import save_state, load_state

# Define a simple module
class Reservoir(drs.Module):
    def __init__(self):
        super().__init__()
        self.capacity = drs.Variable("capacity", 500.0)
        self.volume = drs.Level("volume", initial_value=120.0)

model = Reservoir()

# 1. Access the state dictionary
print("State Dict:", model.state_dict())
# Output: {'capacity.value': 500.0, 'volume.value': 120.0}

# 2. Save state to a JSON file
save_state(model, "reservoir_state.json")

# 3. Modify local model values
model.volume.value = 450.0

# 4. Load the saved state back, restoring original values
load_state(model, "reservoir_state.json")
print("Restored Volume:", model.volume.value)  # Output: 120.0
```

### Exporting Architecture Schema

To export only the structural layout (nested modules and variable types) without saving the actual values, use `export_architecture`:

```python
from drs.serialize import export_architecture

export_architecture(model, "architecture.json")
```

---

## 2. Full Engine Checkpointing (Rewind & Branch)

While `save_state` only captures variable values, `save_checkpoint` captures the complete running state of the `DRSEngine` and its RNGs:
- **Engine State**: Clock time, step count, deadlock step counter.
- **Model Variables**: Variable values, rates, active upper/lower thresholds, and the module references that configured those rates.
- **RNG States**: Random seed states for Python `random` and `numpy.random` to ensure deterministic execution on resume.
- **Telemetry**: Full event logs and history logs recorded up to the checkpoint.

### Example: Branching Scenario Workflow

Suppose you want to run a simulation for 50 time units, and then compare two different routing decisions from that point onward:
- **Branch A**: Increase the inflow rate.
- **Branch B**: Decrease the inflow rate.

Here is how you execute this with checkpoints:

```python
from drs import Module, Variable, Level
from drs.engine import DRSEngine
from drs.serialize import save_checkpoint, load_checkpoint

class FlowSystem(Module):
    def __init__(self):
        super().__init__()
        self.reservoir = Level("reservoir", initial_value=0.0)
        self.inflow_rate = Variable("inflow_rate", 100.0)

    def forward(self):
        self.reservoir.rate = self.inflow_rate.value

# 1. Setup model and engine
model = FlowSystem()
engine = DRSEngine(model)

# 2. Run the simulation to time 50
engine.run(max_time=50.0)
print(f"Time 50 Reservoir Level: {model.reservoir.value}")

# 3. Save the simulation checkpoint
engine.save_checkpoint("time_50_checkpoint.json")

# -------------------------------------------------------------
# BRANCH A: Set inflow rate to 200.0 and run until time 100
# -------------------------------------------------------------
model.inflow_rate.value = 200.0
result_a = engine.run(max_time=100.0)
print(f"Branch A Final Level (time 100): {model.reservoir.value}")

# -------------------------------------------------------------
# BRANCH B: Rewind to time 50, set inflow rate to 50.0, and run
# -------------------------------------------------------------
# Re-instantiate engine (or clear its history) and load checkpoint
engine_b = DRSEngine(FlowSystem())
engine_b.load_checkpoint("time_50_checkpoint.json")

# Modify variable in the restored model
engine_b.model.inflow_rate.value = 50.0

# Run from time 50 to time 100
result_b = engine_b.run(max_time=100.0)
print(f"Branch B Final Level (time 100): {engine_b.model.reservoir.value}")
```

Using full checkpoints guarantees reproducibility across complex simulation scenarios.

Now that you've mastered state management, move on to [Tutorial 5: Telemetry & Custom Callbacks](05_telemetry_callbacks.md) to learn how to monitor simulations and execute custom code on events.