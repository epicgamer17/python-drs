import json
import pytest
from drs import (
    Module,
    DRSEngine,
    Level,
    Variable,
    Telemetry,
    to_dict,
    from_dict,
    save_checkpoint,
    load_checkpoint,
    save_state,
    load_state,
    export_architecture,
)


class SubSystem(Module):
    def __init__(self):
        super().__init__()
        self.capacity = Level("capacity", 100.0, rate=5.0)
        self.custom_param = "test_param"

    def forward(self, *args, **kwargs):
        pass


class SimpleSystem(Module):
    def __init__(self):
        super().__init__()
        self.water_tank = Level("water_tank", 50.0, rate=-2.0)
        self.water_tank.lower_threshold = 0.0
        self.water_tank.upper_threshold = 100.0
        self.status_code = Variable("status_code", 1)
        self.sub = SubSystem()
        self.custom_mode = "auto"

    def forward(self, *args, **kwargs):
        if self.water_tank.value <= 10.0:
            self.water_tank.rate = 10.0
        elif self.water_tank.value >= 90.0:
            self.water_tank.rate = -5.0


def test_module_to_dict_and_from_dict():
    mod = SimpleSystem()
    mod.water_tank.value = 75.0
    mod.water_tank.rate = -3.0
    mod.custom_mode = "manual"

    # Export to dict
    d = mod.to_dict()
    assert isinstance(d, dict)
    assert d["class"] == "SimpleSystem"
    assert "water_tank" in d["variables"]
    assert d["variables"]["water_tank"]["value"] == 75.0
    assert d["attributes"]["custom_mode"] == "manual"
    assert "sub" in d["children"]

    # Verify JSON interoperability without custom encoders
    json_str = json.dumps(d)
    loaded_dict = json.loads(json_str)

    # Restore into new module instance
    new_mod = SimpleSystem()
    new_mod.from_dict(loaded_dict)

    assert new_mod.water_tank.value == 75.0
    assert new_mod.water_tank.rate == -3.0
    assert new_mod.custom_mode == "manual"
    assert new_mod.sub.capacity.value == 100.0


def test_engine_to_dict_and_from_dict():
    mod = SimpleSystem()
    engine = DRSEngine(model=mod, max_step_size=1.0)
    telemetry = Telemetry(mod)
    engine.attach_telemetry(telemetry)

    # Run for a few steps
    engine.run(max_time=5.0)

    # Export engine state to dict
    state_dict = engine.to_dict()
    assert isinstance(state_dict, dict)
    assert state_dict["engine"]["current_time"] >= 5.0
    assert "variables_state" in state_dict
    assert "topology" in state_dict

    # Verify JSON dumps
    json_str = json.dumps(state_dict)
    loaded_dict = json.loads(json_str)

    # Restore into a fresh engine instance
    fresh_mod = SimpleSystem()
    fresh_engine = DRSEngine(model=fresh_mod, max_step_size=1.0)
    fresh_engine.attach_telemetry(Telemetry(fresh_mod))

    fresh_engine.from_dict(loaded_dict)

    assert fresh_engine.current_time == engine.current_time
    assert fresh_engine.step_count == engine.step_count
    assert fresh_mod.water_tank.value == mod.water_tank.value


def test_top_level_to_dict_and_from_dict():
    mod = SimpleSystem()
    d = to_dict(mod)
    assert isinstance(d, dict)

    mod.water_tank.value = 12.0
    from_dict(mod, d)
    assert mod.water_tank.value == 50.0


def test_checkpoint_file_io(tmp_path):
    checkpoint_file = tmp_path / "checkpoint.json"

    mod = SimpleSystem()
    engine = DRSEngine(model=mod, max_step_size=1.0)
    engine.run(max_time=3.0)

    # Save checkpoint via file wrapper using Path
    save_checkpoint(engine, checkpoint_file)

    # Restore via engine method using Path and check return dict
    fresh_mod = SimpleSystem()
    fresh_engine = DRSEngine(model=fresh_mod, max_step_size=1.0)
    loaded_ckpt = fresh_engine.load_checkpoint(checkpoint_file)

    assert isinstance(loaded_ckpt, dict)
    assert fresh_engine.current_time == engine.current_time
    assert fresh_mod.water_tank.value == mod.water_tank.value


def test_save_state_and_export_architecture(tmp_path):
    state_file = tmp_path / "state.json"
    arch_file = tmp_path / "arch.json"

    mod = SimpleSystem()
    mod.water_tank.value = 42.0

    save_state(mod, state_file)
    export_architecture(mod, arch_file)

    with open(state_file, "r", encoding="utf-8") as f:
        state_data = json.load(f)
    assert state_data["water_tank.value"] == 42.0

    with open(arch_file, "r", encoding="utf-8") as f:
        arch_data = json.load(f)
    assert arch_data["class"] == "SimpleSystem"

    new_mod = SimpleSystem()
    loaded_state = load_state(new_mod, state_file)
    assert isinstance(loaded_state, dict)
    assert new_mod.water_tank.value == 42.0
