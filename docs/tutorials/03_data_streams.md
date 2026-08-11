# Tutorial 3: Streaming Inputs & Data Sources

In real-world systems, material flowing through a network is rarely homogeneous. For example, in a chemical processing line, batches of fluid arrive with different volumes and solute concentrations.

To model this, python-drs provides `drs.DataSource` and `drs.DataPoint` to stream batches of discrete parameters into the continuous simulation.

---

## 1. Subclassing DataSource

A `DataSource` behaves like a standard Python Iterator. You subclass it, set up its state, and implement:
1. `__next__(self) -> drs.DataPoint`: Returns the next data record or raises `StopIteration` when the stream is exhausted.

Because `DataSource` inherits from `drs.Module`, any execution context tracking is fully preserved.

```python
import random
from drs import DataSource, DataPoint

class BatchSource(DataSource):
    """Generates incoming batches with varying volume and concentration."""

    def __init__(self, seed: int = 42):
        super().__init__()
        self.rng = random.Random(seed)
        self.total_batches = 10
        self.current_batch = 0

    def __next__(self) -> DataPoint:
        if self.current_batch >= self.total_batches:
            raise StopIteration

        self.current_batch += 1

        # Generate random characteristics for the batch
        volume = self.rng.uniform(4.0, 6.0)      # units of volume
        concentration = self.rng.uniform(0.5, 1.8)  # % solute concentration

        return DataPoint(volume=volume, concentration=concentration)
```

---

## 2. Processing Streams in a Module

You retrieve batches from the datasource using the standard `next()` function or by calling the module (since `__call__` wraps the data retrieval).

Here is a `MixingTank` module that pulls data from a source, loads it into the tank, and discharges a blended mixture with the average solute concentration:

```python
import drs
from drs import Flow

class MixingTank(drs.Module):
    def __init__(self, source: BatchSource):
        super().__init__()
        self.source = source

        # Tank state
        self.volume = drs.Level("volume", initial_value=0.0)
        self.solute = drs.Level("solute", initial_value=0.0)

        # Current batch properties
        self.active_concentration = drs.Variable("active_concentration", 0.0)

    def forward(self):
        # Check if the tank is empty; if so, we can process a new batch
        if self.volume.value <= 1e-6:
            try:
                # Retrieve next batch from source
                batch = next(self.source)

                # Update level parameters
                self.volume.value = batch.volume
                self.solute.value = batch.volume * (batch.concentration / 100.0)
                self.active_concentration.value = batch.concentration

                print(f"Loaded batch: volume={batch.volume:.1f}, concentration={batch.concentration:.2f}%")
            except StopIteration:
                # No more data left in stream
                self.volume.rate = 0.0
                self.solute.rate = 0.0
                return None

        # Discharge well-mixed fluid at 1.0 units of volume per time step
        discharge_rate = min(1.0, self.volume.value)

        # Calculate concentration of outflow (uniform blending assumption)
        concentration_fraction = self.solute.value / self.volume.value if self.volume.value > 0 else 0.0
        solute_discharge = discharge_rate * concentration_fraction

        self.volume.rate = -discharge_rate
        self.solute.rate = -solute_discharge

        # Return outflow as a Flow object containing volume and concentration
        return Flow((discharge_rate, concentration_fraction * 100.0))
```

---

## 3. Running the Simulation

Let's wire up the mixing tank, run the simulation, and print out the telemetry history:

```python
from drs.engine import DRSEngine
from drs.telemetry import Telemetry

# Initialize components
source = BatchSource()
tank = MixingTank(source)

# Create engine and attach telemetry
engine = DRSEngine(tank)
telemetry = Telemetry(tank)
engine.attach_telemetry(telemetry)

# Run the simulation until all batches are processed
result = engine.run(max_time=100.0)

# Print out history of tank contents
df = result.history
print("\nSimulation Log Snapshot:")
print(df[["time", "volume", "active_concentration"]].head(15))
```

Now that you know how to handle complex streaming data in python-drs, check out [Tutorial 4: Checkpointing & State Serialization](04_serialization.md) to learn how to save, restore, and fork simulation states!