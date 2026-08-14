import pytest
from drs import Module, DRSEngine, Level


class DummyModule(Module):
    def __init__(self):
        super().__init__()
        self.water = Level("water", initial_value=10.0)

    def forward(self):
        self.water.rate = -1.0


def test_engine_direct_parameters_defaults():
    model = DummyModule()
    engine = DRSEngine(model)

    assert engine.max_step_size == 0.5
    assert engine.max_deadlock_steps == 20
    assert engine.max_time is None
    assert engine.strict_mode is False


def test_engine_direct_parameters_custom():
    model = DummyModule()
    engine = DRSEngine(
        model,
        max_step_size=0.1,
        max_deadlock_steps=50,
        max_time=15.0,
        strict_mode=True,
    )

    assert engine.max_step_size == 0.1
    assert engine.max_deadlock_steps == 50
    assert engine.max_time == 15.0
    assert engine.strict_mode is True


def test_engine_run_with_engine_max_time():
    model = DummyModule()
    engine = DRSEngine(model, max_time=5.0)
    result = engine.run()
    assert engine.current_time == 5.0
    assert result.sim_time == 5.0


def test_engine_run_with_explicit_max_time_override():
    model = DummyModule()
    engine = DRSEngine(model, max_time=10.0)
    result = engine.run(max_time=3.0)
    assert engine.current_time == 3.0
    assert result.sim_time == 3.0


def test_engine_run_without_max_time_raises():
    model = DummyModule()
    engine = DRSEngine(model)
    with pytest.raises(ValueError, match="max_time must be specified"):
        engine.run()


def test_state_mutation_error_and_open_rates():
    from drs import StateMutationError

    class Sub(Module):
        def __init__(self):
            super().__init__()
            self.stock = Level("stock", initial_value=100.0)

        def forward(self):
            pass

    class ControllerIllegal(Module):
        def __init__(self, sub):
            super().__init__()
            self.sub = sub

        def forward(self):
            # Attempting to mutate value owned by Sub -> raises StateMutationError
            self.sub.stock.value = 500.0

    class ControllerLegal(Module):
        def __init__(self, sub):
            super().__init__()
            self.sub = sub

        def forward(self):
            # Setting rate on Level owned by Sub -> Allowed ("Open Rates")
            self.sub.stock.rate = -5.0

    illegal = ControllerIllegal(Sub())
    engine_illegal = DRSEngine(illegal, max_time=1.0)
    with pytest.raises(StateMutationError, match="Illegal Mutation"):
        engine_illegal.run()

    legal = ControllerLegal(Sub())
    engine_legal = DRSEngine(legal, max_time=1.0)
    result = engine_legal.run()
    assert result.sim_time == 1.0
    assert legal.sub.stock.value == 95.0

