import math
import enum
from typing import Any, Union
from ._execution_context import ExecutionContext
from .exceptions import StateMutationError


def serialize_val(val: Any) -> Any:
    if isinstance(val, enum.Enum):
        return val.name
    if (
        hasattr(val, "name")
        and hasattr(val, "id")
        and not isinstance(val, (int, float, str, bool))
    ):
        return {"__type__": type(val).__name__, "name": val.name}
    if isinstance(val, float):
        if math.isinf(val):
            return "Infinity" if val > 0 else "-Infinity"
        elif math.isnan(val):
            return "NaN"
    return val


def deserialize_val(val: Any) -> Any:
    if val == "Infinity":
        return math.inf
    elif val == "-Infinity":
        return -math.inf
    elif val == "NaN":
        return math.nan
    return val


class Variable:
    """Base class for all domain variables.

    Variables hold named state. They ensure that state changes can be logged
    and accessed seamlessly.

    Attributes:
        name (str): The unique name of the variable.
    """

    def __init__(self, name: str, initial_value: Any = 0.0, owner: Any = None) -> None:
        """
        Initialize a new Variable.

        Args:
            name: The unique name of the variable.
            initial_value: The starting value (default: 0.0).
            owner: The owning Module instance (default: None).
        """
        self.name = name
        self._value = initial_value
        self._owner = owner

    # Allows accessing directly as a class descriptor attribute on owner modules
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._value

    # Automatic cast to float in numeric operations
    def __float__(self) -> float:
        return float(self._value)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}: {self._value}>"

    @property
    def value(self) -> Any:
        """Get the current value of the variable."""
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        """Set the value of the variable."""
        current_actor = ExecutionContext.get_current()
        if (
            current_actor is not None
            and self._owner is not None
            and current_actor is not self._owner
        ):
            raise StateMutationError(
                f"Illegal Mutation: '{type(current_actor).__name__}' attempted to modify state "
                f"'{self.name}' owned by '{type(self._owner).__name__}'. Use flow rates instead!"
            )

        if self._value != val:
            engine = ExecutionContext.get_engine()
            if engine and getattr(engine, "telemetry", None):
                engine.telemetry.log_event(
                    time=engine.current_time,
                    event_type="STATE_CHANGE",
                    source=type(current_actor).__name__ if current_actor else "External",
                    details={
                        "variable": self.name,
                        "old_value": self._value,
                        "new_value": val,
                    },
                )
            self._value = val

    @property
    def rate(self) -> float:
        raise AttributeError(
            f"'{type(self).__name__}' has no attribute 'rate'. "
            f"Only drs.Level supports .rate. Use drs.Level() for quantities that flow."
        )

    @rate.setter
    def rate(self, val: Union[float, tuple[float, float, float]]) -> None:
        raise AttributeError(
            f"Cannot set .rate on '{type(self).__name__}'. "
            f"Only drs.Level supports .rate."
        )

    def _val(self, other: Any) -> Any:
        return other._value if isinstance(other, Variable) else other

    def __add__(self, other: Any) -> Any:
        return self._value + self._val(other)

    def __radd__(self, other: Any) -> Any:
        return self._val(other) + self._value

    def __sub__(self, other: Any) -> Any:
        return self._value - self._val(other)

    def __rsub__(self, other: Any) -> Any:
        return self._val(other) - self._value

    def __mul__(self, other: Any) -> Any:
        return self._value * self._val(other)

    def __rmul__(self, other: Any) -> Any:
        return self._val(other) * self._value

    def __truediv__(self, other: Any) -> Any:
        r = self._val(other)
        return self._value / r if r != 0 else 0.0

    def __rtruediv__(self, other: Any) -> Any:
        l = self._val(other)
        return l / self._value if self._value != 0 else 0.0

    def __pow__(self, other: Any) -> Any:
        return self._value ** self._val(other)

    def __rpow__(self, other: Any) -> Any:
        return self._val(other) ** self._value

    def __neg__(self) -> Any:
        return -self._value

    def __pos__(self) -> Any:
        return +self._value

    def __abs__(self) -> Any:
        return abs(self._value)

    def __lt__(self, other: Any) -> bool:
        return self._value < self._val(other)

    def __le__(self, other: Any) -> bool:
        return self._value <= self._val(other)

    def __gt__(self, other: Any) -> bool:
        return self._value > self._val(other)

    def __ge__(self, other: Any) -> bool:
        return self._value >= self._val(other)

    def __hash__(self) -> int:
        return id(self)


class Level(Variable):
    """A variable that accumulates over time based on a rate.

    Levels are the primary way to model physical quantities that flow or change
    continuously over time (e.g., volume in a tank, energy in a battery).

    Attributes:
        upper_threshold (float): The maximum limit for the level. Defaults to math.inf.
        lower_threshold (float): The minimum limit for the level. Defaults to -math.inf.
    """

    def __init__(
        self, name: str, initial_value: float = 0.0, rate: float = 0.0
    ) -> None:
        """
        Initialize a new Level.

        Args:
            name: The unique name of the level.
            initial_value: The starting value (default: 0.0).
            rate: The initial rate of change (default: 0.0).
        """
        super().__init__(name, initial_value)
        self._rate = rate
        self.upper_threshold = math.inf
        self.lower_threshold = -math.inf

    @property
    def rate(self) -> float:
        """
        Get the current rate of change.

        Returns:
            float: The rate at which the level is currently accumulating per time unit.
        """
        return self._rate

    @rate.setter
    def rate(self, val: Union[float, tuple[float, float, float]]) -> None:
        """
        Set the rate of change.

        Args:
            val (Any): Can be a single float representing the new rate, or a tuple
                of `(rate, lower_threshold, upper_threshold)`.

        Raises:
            ValueError: If a tuple is provided but it does not have exactly 3 elements.
        """
        if isinstance(val, tuple):
            if len(val) == 3:
                self._rate, self.lower_threshold, self.upper_threshold = val
            else:
                raise ValueError(f"Rate tuple must be (rate, lower, upper), got {val}")
        else:
            self._rate = val

    def _update(self, dt: float) -> None:
        """
        [INTERNAL] Step the level forward in time based on its current rate.

        Args:
            dt (float): The amount of time to simulate.
        """
        self.value += self.rate * dt


class Timer(Level):
    """A specialized level used to track time.

    Timers are simply Levels that accumulate at a default rate of 1.0 (or -1.0 for countdowns).
    """

    def __init__(
        self, name: str, initial_value: float = 0.0, rate: float = 1.0
    ) -> None:
        """
        Initialize a Timer.

        Args:
            name: The unique name of the timer.
            initial_value: The starting time value (default: 0.0).
            rate: The speed of time (default: 1.0).
        """
        super().__init__(name, initial_value, rate)

    def reset(self) -> None:
        """
        Reset the timer value back to 0.0.

        This sets the absolute value of the timer to 0, but does not modify the rate.
        """
        self.value = 0.0
