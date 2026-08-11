# Tutorial 3: Streaming Inputs & Data Sources

In real-world operations, material flowing through a system is rarely homogeneous. For example, in a mining operation, different truckloads of ore have different ore grades (percentage of valuable metal) and impurities. 

To model this, Mining-DRS provides `drs.DataSource` and `drs.DataPoint` to stream batches of discrete parameters into the continuous simulation.

You can find the runnable Python code for this tutorial in [03_data_streams.py](file:///Users/jonathanlamontange-kratz/Documents/GitHub/mining-drs/examples/tutorial/03_data_streams.py).

---

## 1. Subclassing DataSource

A `DataSource` behaves like a standard Python Iterator. You subclass it, set up its state, and implement:
1. `__next__(self) -> drs.DataPoint`: Returns the next data record or raises `StopIteration` when the stream is exhausted.

Because `DataSource` inherits from `drs.Module`, any execution context tracking is fully preserved.

```python
import random
from drs import DataSource, DataPoint

class MineTruckSource(DataSource):
    """Generates continuous truck arrivals with varying mass and metal grade."""

    def __init__(self, seed: int = 42):
        super().__init__()
        self.rng = random.Random(seed)
        self.total_trucks = 10
        self.current_truck = 0

    def __next__(self) -> DataPoint:
        if self.current_truck >= self.total_trucks:
            raise StopIteration
        
        self.current_truck += 1
        
        # Generate random characteristics for the truck's load
        mass = self.rng.uniform(40.0, 60.0)    # tons of rock
        grade = self.rng.uniform(0.5, 1.8)     # % metal grade
        
        return DataPoint(mass=mass, grade=grade)
```

---

## 2. Processing Streams in a Module

You retrieve batches from the datasource using the standard `next()` function or by calling the module (since `__call__` wraps the data retrieval).

Here is a `Conveyor` module that pulls data from a source and loads it into a stockpile, calculating the average metal grade of the stockpile dynamically:

```python
import drs
from drs import Flow

class OreConveyor(drs.Module):
    def __init__(self, source: MineTruckSource):
        super().__init__()
        self.source = source
        
        # Stockpile state
        self.ore_mass = drs.Level("ore_mass", initial_value=0.0)
        self.metal_mass = drs.Level("metal_mass", initial_value=0.0)
        
        # Current batch properties
        self.active_grade = drs.Variable("active_grade", 0.0)

    def forward(self):
        # Check if the stockpile is empty; if so, we can process a new batch
        if self.ore_mass.value <= 1e-6:
            try:
                # Retrieve next truck from source
                batch = next(self.source)
                
                # Update level parameters
                self.ore_mass.value = batch.mass
                self.metal_mass.value = batch.mass * (batch.grade / 100.0)
                self.active_grade.value = batch.grade
                
                print(f"Loaded truck: mass={batch.mass:.1f}t, grade={batch.grade:.2f}%")
            except StopIteration:
                # No more data left in stream
                self.ore_mass.rate = 0.0
                self.metal_mass.rate = 0.0
                return None

        # Conveyor transports ore to processing at 10 tons per hour
        discharge_rate = min(10.0, self.ore_mass.value)
        
        # Calculate grade of outflow (uniform blending assumption)
        grade_fraction = self.metal_mass.value / self.ore_mass.value if self.ore_mass.value > 0 else 0.0
        metal_discharge = discharge_rate * grade_fraction
        
        self.ore_mass.rate = -discharge_rate
        self.metal_mass.rate = -metal_discharge
        
        # Return outflow as a Flow object containing mass and average grade
        return Flow((discharge_rate, grade_fraction * 100.0))
```

---

## 3. Running the Simulation

Let's wire up the conveyor, run the simulation, and print out the audit logs from the telemetry history:

```python
from drs.engine import DRSEngine
from drs.telemetry import Telemetry

# Initialize components
source = MineTruckSource()
conveyor = OreConveyor(source)

# Create engine and attach telemetry
engine = DRSEngine(conveyor)
telemetry = Telemetry(conveyor)
engine.attach_telemetry(telemetry)

# Run the simulation until all trucks are processed
result = engine.run(max_time=100.0)

# Print out history of stockpile contents
df = result.history
print("\nSimulation Log Snapshot:")
print(df[["time", "ore_mass", "active_grade"]].head(15))
```

Now that you know how to handle complex streaming data in Mining-DRS, check out [Tutorial 4: Checkpointing & State Serialization](04_serialization.md) to learn how to save, restore, and fork simulation states!
