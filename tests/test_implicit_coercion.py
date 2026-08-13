import pytest
import math
from drs import Module, DRSEngine, Variable, Level, Timer
from drs._execution_context import ExecutionContext


class MineModule(Module):
    def __init__(self):
        super().__init__()
        self.cumulative_extracted_mass = Level("cumulative_extracted_mass", initial_value=100.0)
        self.warming_period = Variable("warming_period", initial_value=10.0)
        self.active_time = Variable("active_time", initial_value=2.0)

    def forward(self):
        # Calculate throughput directly without .value
        self.throughput = (self.cumulative_extracted_mass - self.warming_period) / self.active_time


class ClassDescriptorModule(Module):
    # Variables declared as class attributes (Descriptor protocol)
    x = Variable("x", 42.0)
    y = Level("y", initial_value=8.0)


def test_float_coercion_and_direct_arithmetic():
    mine = MineModule()
    
    # Direct arithmetic without .value
    throughput = (mine.cumulative_extracted_mass - mine.warming_period) / mine.active_time
    assert throughput == 45.0

    # float() coercion
    assert float(mine.cumulative_extracted_mass) == 100.0
    assert float(mine.warming_period) == 10.0
    assert math.sqrt(mine.active_time) == math.sqrt(2.0)


def test_class_descriptor_arithmetic():
    mod = ClassDescriptorModule()
    # Class attributes access __get__ descriptor method returning float/sim_value
    assert mod.x + mod.y == 50.0
    assert mod.x / 2.0 == 21.0


def test_repr():
    var = Variable("mass", 50.5)
    lvl = Level("tank", 100.0)
    timer = Timer("clock", 0.0)

    assert repr(var) == "<Variable mass: 50.5>"
    assert repr(lvl) == "<Level tank: 100.0>"
    assert repr(timer) == "<Timer clock: 0.0>"


def test_descriptor_protocol_get():
    # Accessed on class -> returns descriptor object
    assert isinstance(ClassDescriptorModule.x, Variable)
    assert ClassDescriptorModule.x.name == "x"

    # Accessed on instance -> returns current value via __get__
    mod = ClassDescriptorModule()
    assert mod.x == 42.0
    assert mod.y == 8.0


def test_tracing_mode_safe_float_and_repr():
    var = Variable("var", 12.5)
    
    # Set tracing mode on ExecutionContext
    ExecutionContext.set_tracing(True)
    try:
        val = var._get_current_val()
        assert val is var
        assert float(var) == 12.5
        assert repr(var) == "<Variable var: 12.5>"
    finally:
        ExecutionContext.set_tracing(False)


def test_dependency_logging_without_dot_value():
    class ReaderModule(Module):
        def __init__(self, source_var):
            super().__init__()
            self.source_var = source_var
            self.read_val = Variable("read_val", 0.0)

        def forward(self):
            # Reading source_var directly without .value
            self.read_val.value = float(self.source_var) * 2.0

    writer = MineModule()
    reader = ReaderModule(writer.cumulative_extracted_mass)

    # Run one step inside execution context
    ExecutionContext.push(reader)
    try:
        val = reader.source_var._get_current_val()
    finally:
        ExecutionContext.pop()

    # Verify dependency incoming edge recorded
    assert any(dep[1] is writer.cumulative_extracted_mass for dep in reader._dependencies)
