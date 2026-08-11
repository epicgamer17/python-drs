# python-drs — Discrete Rate Simulation (DRS) Framework for Python

[![PyPI version](https://img.shields.io/pypi/v/python-drs.svg)](https://pypi.org/project/python-drs/)
[![Python versions](https://img.shields.io/pypi/pyversions/python-drs.svg)](https://pypi.org/project/python-drs/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**python-drs** is an open-source, PyTorch-inspired, **event-driven Discrete Rate Simulation (DRS)** framework for Python. It models systems where quantities flow continuously over time — water networks, chemical processing, electrical grids, energy storage, traffic, and supply chains — dramatically faster than traditional fixed-step simulation.

Discrete Rate Simulation is a hybrid of discrete-event simulation and continuous simulation: instead of ticking through time at fixed intervals, the engine calculates *exactly* when the next limit (threshold) will be reached, jumps the simulation clock to that precise moment, and triggers the matching state transition. The result is a Python simulation library that runs years of operation in a fraction of a second — and **never misses a limit**.

---

## Why Discrete Rate Simulation?

| Fixed-step simulation | Discrete Rate Simulation (DRS) |
|-----------------------|-------------------------------|
| Checks the system at every interval | Computes *exactly* when the next limit is hit |
| Can miss events between ticks | Never misses a limit |
| Slow for tight tolerances | Fast, event-driven time jumping |
| Threshold logic bolted on | Thresholds are first-class citizens |

Discrete Rate Simulation is ideal for hybrid systems where continuous physics (filling, draining, heating, discharging) meets discrete thresholds (full, empty, minimum, maximum, switch points).

---

## Key Features

- **Event-driven time stepping** — simulate years of operation in seconds by jumping directly from event to event
- **PyTorch-style architecture** — every model is a `Module` that owns `Variable`, `Level`, and `Timer` state, with `forward()` dynamics and **automatic dependency tracking**
- **Continuous-flow modeling** — `Level`s accumulate quantity over time (like an integral in `dt`); protected `Flow` objects safely pass physical quantities between modules
- **Built-in telemetry** — every state change is logged and plotted as a pandas `DataFrame` without custom tracking code
- **Fail-fast guardrails** — the engine stops you from breaking the physics of your model (e.g. draining an empty tank) and detects deadlocks
- **Checkpointing & serialization** — save, load, and fork simulation states; export your architecture
- **Callbacks** — hook custom logic into runs, including a Rich progress bar
- **Streaming inputs** — feed discrete data streams into continuous dynamics
- **SciPy/NumPy/Pandas ecosystem** — first-class integration with the Python scientific stack
- **Pure Python** — works on Python 3.9+, no external solver required

---

## Installation

Install from PyPI:

```bash
pip install python-drs
```

Optional extras:

```bash
pip install python-drs[progress]   # Rich progress bar
```

---

## Quickstart

Model a tank that fills at a constant rate and watch the engine jump to the exact moment it overflows:

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

Learn the core concepts step by step: [Tutorial 1: Introduction to DRS](docs/tutorials/01_introduction.md).

---

## How the Engine Works

Every simulation follows the same repeating loop:

1. **Evaluate `forward()` passes** — modules and controllers compute the instantaneous rates of the system.
2. **Find the next event** — the engine calculates how long until any `Level` crosses one of its thresholds.
3. **Jump time** — the simulation clock advances by exactly that amount, and all levels are integrated forward.
4. **Trigger transitions** — the system detects the crossed limit and transitions to the appropriate state.
5. **Repeat.**

Because time jumps from event to event rather than advancing at fixed steps, python-drs scales to long-horizon problems that are intractable with naive fixed-step solvers.

---

## Use Cases

- **Water networks & hydraulics** — storage tanks, reservoirs, pumping stations, pipe flow
- **Chemical & process engineering** — reactors, tanks, batch processes, separations
- **Electrical grids & energy storage** — charge/discharge cycles, grid balancing, batteries
- **Supply chains & logistics** — inventory, buffer stock, material flow, demand shocks
- **Manufacturing** — production lines, work-in-progress, equipment states
- **Traffic & transportation** — queue accumulation, congestion thresholds

If your system is best described by **continuous flow crossing discrete thresholds**, it is a Discrete Rate Simulation — and python-drs is the Python library built for it.

---

## Documentation

Full guides, tutorials, and API reference live in the [`docs/`](docs/):

- [Tutorial 1: Introduction to DRS](docs/tutorials/01_introduction.md)
- [Tutorial 2: Advanced Core Dynamics & Guardrails](docs/tutorials/02_advanced_dynamics.md)
- [Tutorial 3: Streaming Inputs & Data Sources](docs/tutorials/03_data_streams.md)
- [Tutorial 4: Checkpointing & State Serialization](docs/tutorials/04_serialization.md)
- [Tutorial 5: Telemetry & Custom Callbacks](docs/tutorials/05_telemetry_callbacks.md)
- [Tutorial 6: Design Patterns: Operating Modes](docs/tutorials/06_operating_modes.md)
- [API Reference](docs/api/engine.md)

---

## Related

Looking for a Python alternative to discrete-rate simulation approaches in Simulink® or Modelica? python-drs brings PyTorch-like ergonomics to **event-driven, continuous-flow simulation** and lives on [PyPI](https://pypi.org/project/python-drs/).

## License

MIT — see [LICENSE](LICENSE).