# python-drs

A PyTorch-inspired, event-driven **Discrete Rate Simulation (DRS)** framework for modeling systems where material flows continuously over time.

Instead of ticking through time at fixed intervals, DRS calculates *exactly* when the next limit (threshold) will be hit, jumps the simulation clock to that precise moment, and triggers the matching state transition. The result is a simulation that runs in a fraction of the time of fixed-step models — and never misses a limit.

## Features

- **Event-driven time stepping** — simulate years of operation in seconds
- **PyTorch-style architecture** — `Module`, `Variable`, and `Level` compose into hierarchies with automatic dependency tracking
- **Built-in telemetry** — every state change is logged and plotted without custom tracking code
- **Fail-fast guardrails** — the engine stops you from breaking the physics of your model (e.g. draining an empty tank)
- **Applicable to any continuous-flow system** — water networks, chemical processing, electrical grids, traffic, and more

## Installation

```bash
pip install python-drs
```

Optional extras:

```bash
pip install python-drs[progress]   # Rich progress bar
```

## Quickstart

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

## Documentation

Full guides, tutorials, and API reference live in the [`docs/`](https://github.com/epicgamer17/python-drs/tree/main/docs) directory.

## License

MIT — see [LICENSE](LICENSE).