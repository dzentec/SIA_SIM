"""Deterministic discrete simulation clock for SIA Simulation."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SimulationClockProtocol(Protocol):
    """Protocol defining the interface for simulation clock implementations."""

    @property
    def time_ms(self) -> int:
        """Current simulation time in integer milliseconds."""
        ...

    @property
    def tick_ms(self) -> int:
        """Default step interval in integer milliseconds (e.g. 10 ms for 100 Hz)."""
        ...

    def advance(self, dt_ms: int | None = None) -> int:
        """Advance simulation time by dt_ms (or default tick_ms) and return new time_ms."""
        ...

    def reset(self, start_time_ms: int = 0) -> None:
        """Reset simulation time to start_time_ms."""
        ...


class SimulationClock:
    """Deterministic integer step simulation clock.

    MVP target: 10 ms tick / 100 Hz simulation frequency.
    Time is strictly monotonic and non-negative. Zero reliance on wall-clock time.
    """

    def __init__(self, tick_ms: int = 10, start_time_ms: int = 0) -> None:
        if tick_ms <= 0:
            raise ValueError(f"tick_ms must be positive, got {tick_ms}")
        if start_time_ms < 0:
            raise ValueError(f"start_time_ms must be non-negative, got {start_time_ms}")

        self._tick_ms = tick_ms
        self._time_ms = start_time_ms

    @property
    def time_ms(self) -> int:
        """Current simulation time in integer milliseconds."""
        return self._time_ms

    @property
    def tick_ms(self) -> int:
        """Default step interval in integer milliseconds."""
        return self._tick_ms

    @property
    def time_seconds(self) -> float:
        """Current simulation time in decimal seconds."""
        return self._time_ms / 1000.0

    def advance(self, dt_ms: int | None = None) -> int:
        """Advance simulation time by dt_ms (or default tick_ms) and return new time_ms."""
        step = self._tick_ms if dt_ms is None else dt_ms
        if step < 0:
            raise ValueError(f"Cannot advance clock by negative step: {step} ms")
        self._time_ms += step
        return self._time_ms

    def reset(self, start_time_ms: int = 0) -> None:
        """Reset simulation time to start_time_ms."""
        if start_time_ms < 0:
            raise ValueError(f"start_time_ms must be non-negative, got {start_time_ms}")
        self._time_ms = start_time_ms

    def __repr__(self) -> str:
        return f"SimulationClock(time_ms={self._time_ms}, tick_ms={self._tick_ms})"
