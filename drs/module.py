import math
from typing import Iterator, Any, Optional
from .variables import Variable, Level
from ._execution_context import ExecutionContext
from .data_source import DataPoint
from .flow import Flow


class Module:
    """Base class for all DRS models and sub-components.

    Modules are the fundamental building blocks of a simulation. They automatically
    register any `Variable` or `Module` assigned as an attribute, mimicking the
    behavior of PyTorch's `nn.Module`.

    Attributes:
        parent (Optional[Module]): The parent module that owns this module.
    """

    def __init__(self) -> None:
        """Initialize the module and its internal registries."""
        self._variables = {}
        self._modules = {}
        self.parent = None
        self._post_step_hooks = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the forward pass while managing the ExecutionContext.

        This method acts as a wrapper around `forward()`. It pushes this module
        onto the execution stack and pops it after `forward()` completes.

        Args:
            *args: Positional arguments passed to `forward()`.
            **kwargs: Keyword arguments passed to `forward()`.

        Returns:
            Any: The result of the `forward()` pass.

        Raises:
            RuntimeError: If invalid types are returned.
        """
        ExecutionContext.push(self)
        try:
            result = self.forward(*args, **kwargs)

            if isinstance(result, tuple):
                for res in result:
                    if not isinstance(res, (Flow, DataPoint)):
                        raise RuntimeError(
                            f"Tuple returned from '{type(self).__name__}.forward()' "
                            f"must contain only drs.Flow or drs.DataPoint objects."
                        )
                    res._source = self
                return result

            if isinstance(self, DataSource):
                if result is None:
                    raise RuntimeError(
                        f"'{type(self).__name__}.forward()' must return drs.DataPoint or drs.Flow. "
                        f"DataSource subclasses cannot return None."
                    )
                if not isinstance(result, (Flow, DataPoint)):
                    raise RuntimeError(
                        f"'{type(self).__name__}.forward()' returned "
                        f"'{type(result).__name__}', not drs.Flow or drs.DataPoint."
                    )

            if result is not None and not isinstance(result, (Flow, DataPoint)):
                raise RuntimeError(
                    f"'{type(self).__name__}.forward()' returned "
                    f"'{type(result).__name__}', not a drs.Flow or drs.DataPoint. "
                    f"Inter-module communication must use drs.Flow or drs.DataPoint."
                )

            if isinstance(result, (Flow, DataPoint)):
                result._source = self

            return result
        finally:
            ExecutionContext.pop()

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """
        Define the physics and logic of the module.

        This method must be implemented by all subclasses. It is called on every
        time step to update rates and determine flows.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Any: Typically a `drs.Flow`, `drs.DataPoint`, or a tuple of them.
        """
        raise NotImplementedError("Module subclasses must implement forward()")

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        if hasattr(self, "_variables"):
            self._variables.pop(name, None)
        if hasattr(self, "_modules") and name != "parent":
            self._modules.pop(name, None)

        if isinstance(value, Variable):
            if not hasattr(self, "_variables"):
                raise AttributeError(
                    "Cannot assign variable before Module.__init__() call"
                )
            self._variables[name] = value
            if getattr(value, "_owner", None) is None:
                value._owner = self
        elif isinstance(value, Module) and name != "parent":
            if not hasattr(self, "_modules"):
                raise AttributeError(
                    "Cannot assign module before Module.__init__() call"
                )
            self._modules[name] = value
            if not getattr(value, "parent", None):
                value.parent = self

        super().__setattr__(name, value)

    def variables(self) -> Iterator[Variable]:
        """
        Recursively yield all variables owned by this module and its sub-modules.

        Returns:
            Iterator[Variable]: An iterator over all unique variables in the hierarchy.
        """
        seen = set()

        def _get_vars(module):
            for var in module._variables.values():
                var_id = id(var)
                if var_id not in seen:
                    seen.add(var_id)
                    yield var
            for mod in module._modules.values():
                yield from _get_vars(mod)

        yield from _get_vars(self)

    def modules(self) -> Iterator["Module"]:
        """
        Recursively yield this module and all nested sub-modules.

        Returns:
            Iterator[Module]: An iterator over the module hierarchy.
        """
        for _, module in self.named_modules():
            yield module

    def named_modules(self, prefix: str = "") -> Iterator[tuple[str, "Module"]]:
        """
        Recursively yield `(path, module)` pairs using PyTorch-style names.

        Args:
            prefix (str): The prefix to prepend to the paths.

        Returns:
            Iterator[tuple[str, Module]]: An iterator of `(path, module)` tuples.
        """
        seen = set()

        def _get_modules(module, module_prefix):
            module_id = id(module)
            if module_id in seen:
                return
            seen.add(module_id)
            yield module_prefix, module

            for name, sub_mod in module._modules.items():
                sub_prefix = name if not module_prefix else f"{module_prefix}.{name}"
                yield from _get_modules(sub_mod, sub_prefix)

        yield from _get_modules(self, prefix)

    def _zero_rates(self) -> None:
        """
        [INTERNAL] Zero out rates and remove thresholds for all Levels before the next rate update.
        """
        for var in self.variables():
            if isinstance(var, Level):
                var._rate = 0.0
                var.upper_threshold = math.inf
                var.lower_threshold = -math.inf

    def initialize_state(self) -> None:
        """
        Override this to set up initial state before the simulation starts.

        This is called once by the engine before the first time step.
        """
        pass

    def is_terminating_condition_met(self) -> bool:
        """
        Override this to define custom stopping conditions.

        Returns:
            bool: True if the simulation should stop, False otherwise.
        """
        return False

    def state_dict(self, prefix: str = "") -> dict[str, Any]:
        """
        Returns a dictionary containing the entire state of the module.
        Keys are dotted paths to variable values (e.g., 'submodule.variable.value').
        """
        state = {}
        for name, var in self._variables.items():
            key_base = f"{prefix}.{name}" if prefix else name
            state[f"{key_base}.value"] = var.value

        for name, module in self._modules.items():
            module_prefix = f"{prefix}.{name}" if prefix else name
            state.update(module.state_dict(prefix=module_prefix))

        return state

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        """
        Copies state from state_dict into this module and its descendants.
        """
        for key, value in state_dict.items():
            if not key.endswith(".value"):
                continue
            key_base = key[:-6]  # remove .value
            parts = key_base.split(".")
            var_name = parts[-1]
            mod_path = parts[:-1]

            # Navigate to the correct module
            current_mod = self
            try:
                for part in mod_path:
                    current_mod = current_mod._modules[part]
                current_mod._variables[var_name].value = value
            except KeyError:
                import logging

                logging.getLogger(__name__).warning(
                    f"Key '{key}' found in state_dict but not in module hierarchy."
                )

    def to_dict(self, root: Optional["Module"] = None) -> dict[str, Any]:
        """
        Returns a structural JSON-serializable representation of the module architecture and state.
        """
        from .variables import Level, serialize_val

        if root is None:
            root = self

        def _to_dict_serialize_val(val: Any) -> Any:
            return serialize_val(val)

        children = {}
        for name, mod in self._modules.items():
            children[name] = mod.to_dict(root)

        variables = {}
        for name, var in self._variables.items():
            var_info = {
                "class": type(var).__name__,
                "value": _to_dict_serialize_val(var._value),
            }
            if isinstance(var, Level):
                var_info["rate"] = _to_dict_serialize_val(var._rate)
                var_info["lower_threshold"] = _to_dict_serialize_val(
                    var.lower_threshold
                )
                var_info["upper_threshold"] = _to_dict_serialize_val(
                    var.upper_threshold
                )
            variables[name] = var_info

        layout = getattr(self, "layout", getattr(self, "metadata", {}))
        if not isinstance(layout, dict):
            layout = {"value": str(layout)}

        attributes = {}
        import json
        from .variables import Variable

        # Exclude reserved framework attributes
        RESERVED_KEYS = {
            "parent",
            "config",
            "telemetry",
            "layout",
            "global_time",
        }

        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if k in RESERVED_KEYS:
                continue
            if isinstance(v, (Module, Variable)):
                continue
            if isinstance(v, (int, float, str, bool, list, dict)) or v is None:
                try:
                    json.dumps(v)
                    attributes[k] = v
                except Exception:
                    pass

        return {
            "class": type(self).__name__,
            "layout": layout,
            "variables": variables,
            "attributes": attributes,
            "children": children,
        }

    def from_dict(self, state_dict: dict[str, Any]) -> None:
        """
        Restores module state (variable values, rates, thresholds, custom attributes, and submodules)
        from a Python dictionary exported via to_dict() or a flat state dict.
        """
        from .variables import deserialize_val

        # Handle flat state dict (e.g., keys ending with .value)
        if any(k.endswith(".value") for k in state_dict.keys()):
            self.load_state_dict(state_dict)
            return

        # Restore user attributes
        saved_attrs = state_dict.get("attributes", {})
        for k, v in saved_attrs.items():
            setattr(self, k, v)

        # Restore variables
        saved_vars = state_dict.get("variables", {})
        for var_name, var_info in saved_vars.items():
            if var_name not in self._variables:
                continue
            var = self._variables[var_name]
            if isinstance(var_info, dict):
                if "value" in var_info and var_info["value"] is not None:
                    var._value = deserialize_val(var_info["value"])
                if "rate" in var_info and var_info["rate"] is not None and hasattr(var, "_rate"):
                    var._rate = deserialize_val(var_info["rate"])
                if "lower_threshold" in var_info and var_info["lower_threshold"] is not None and hasattr(var, "lower_threshold"):
                    var.lower_threshold = deserialize_val(var_info["lower_threshold"])
                if "upper_threshold" in var_info and var_info["upper_threshold"] is not None and hasattr(var, "upper_threshold"):
                    var.upper_threshold = deserialize_val(var_info["upper_threshold"])
            else:
                var._value = deserialize_val(var_info)

        # Restore submodules
        saved_children = state_dict.get("children", {})
        for child_name, child_state in saved_children.items():
            if child_name in self._modules:
                self._modules[child_name].from_dict(child_state)

    def register_post_step_hook(self, hook_fn: Any) -> None:
        """Registers a callback to be run after every engine step."""
        self._post_step_hooks.append(hook_fn)

    def _run_post_step_hooks(self, current_time: float) -> None:
        """
        [INTERNAL] Execute all registered post-step callback functions.

        Power User Note: Called automatically by the DRSEngine after time integration.
        """
        for hook in self._post_step_hooks:
            hook(current_time)


class DataSource(Module):
    """Yields ``DataPoint`` batches one at a time.

    Subclass and implement ``__next__`` to define the data stream.
    Raise ``StopIteration`` when the stream is exhausted::

        class MySource(DataSource):
            def __init__(self):
                super().__init__()
                self._data = [DataPoint(x=1), DataPoint(x=2)]
                self._index = 0

            def __next__(self) -> DataPoint:
                if self._index >= len(self._data):
                    raise StopIteration
                point = self._data[self._index]
                self._index += 1
                return point
    """

    def __init__(self) -> None:
        """Initialize the DataSource."""
        super().__init__()

    def __iter__(self) -> Iterator[DataPoint]:
        """Return the iterator object itself."""
        return self

    def __next__(self) -> DataPoint:
        """Yield the next DataPoint in the sequence."""
        raise StopIteration
