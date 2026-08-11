# python-drs

Welcome to **python-drs**, a PyTorch-inspired, event-driven **Discrete Rate Simulation (DRS)** framework.

DRS models systems where quantities flow continuously over time — water networks, electrical grids, traffic, chemical processing, supply chains, and more. Instead of stepping through time at fixed intervals, the engine calculates *exactly* when the next limit will be hit, jumps the simulation clock to that precise moment, and triggers the matching state transition.

- **Blazing fast** — because time jumps from event to event, years of operation can be simulated in a fraction of a second.
- **Fail-fast safety** — the framework stops you with clear errors if you break the physics of your model (e.g., draining an empty tank).
- **PyTorch-inspired architecture** — everything is a `Module` that automatically tracks its own state, so writing a simulation feels like building a neural network.

---

## 1. The Core Idea

Most simulations use a **fixed-step** approach. Imagine watching a tank fill, checking it exactly once every minute.

- *The problem:* If it overflows at 1 minute and 30 seconds, you won't notice until minute 2.
- *The workaround:* Check every second — but that makes the simulation slow.

**Discrete Rate Simulation** is different. The engine looks at the fill rate, computes *exactly* when the tank will be full, sets an alarm for that moment, and lets the simulation "jump" forward in time. It runs incredibly fast and never misses a limit.

---

## 2. How the Engine Works

Every simulation follows the same repeating loop:

1. **Evaluate `forward()` passes** — modules and controllers compute the instantaneous rates of the system.
2. **Find the next event** — the engine calculates how long until any `Level` crosses one of its thresholds.
3. **Jump time** — the simulation clock advances by exactly that amount, and all levels are integrated forward.
4. **Trigger transitions** — the system detects the crossed limit and transitions to the appropriate state.
5. **Repeat.**

---

## 3. Getting Started

```python
from drs import DRSEngine, Module, Level

class Tank(Module):
    def forward(self):
        # Fill at 50 units per time step
        self.volume.rate = 50.0

model = Tank()
model.volume = Level("Volume", initial_value=100.0)

engine = DRSEngine(model)
result = engine.run(max_time=20.0)
print(result.summary())
```

Every component is a `drs.Module` that owns its physical state as a `drs.Level` (something that fills or empties). Modules can be nested into hierarchies, and the engine tracks dependencies automatically.

---

## 4. Where to Go Next

- **[Tutorial 1: Introduction to DRS](tutorials/01_introduction.md)** — core types, modules, and your first simulation.
- **[Tutorial 2: Advanced Core Dynamics & Guardrails](tutorials/02_advanced_dynamics.md)** — event-driven time jumping and fail-fast safety rules.
- **[Tutorial 3: Streaming Inputs & Data Sources](tutorials/03_data_streams.md)** — feeding discrete data streams into a continuous simulation.
- **[Tutorial 4: Checkpointing & State Serialization](tutorials/04_serialization.md)** — saving, loading, and forking simulation states.
- **[Tutorial 5: Telemetry & Custom Callbacks](tutorials/05_telemetry_callbacks.md)** — monitoring runs and hooking custom logic into the engine.
- **[Tutorial 6: Design Patterns: Operating Modes](tutorials/06_operating_modes.md)** — controllers and mode-driven routing.

The [API reference](api/engine.md) documents the full public interface.