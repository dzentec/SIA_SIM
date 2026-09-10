"""Unit tests for SimulationClock."""

import pytest

from sia_sim.core.clock import SimulationClock, SimulationClockProtocol


def test_clock_implements_protocol() -> None:
    clock = SimulationClock()
    assert isinstance(clock, SimulationClockProtocol)


def test_clock_default_initialization() -> None:
    clock = SimulationClock()
    assert clock.time_ms == 0
    assert clock.tick_ms == 10  # 100 Hz
    assert clock.time_seconds == 0.0


def test_clock_advance_default() -> None:
    clock = SimulationClock(tick_ms=10)
    assert clock.advance() == 10
    assert clock.time_ms == 10
    assert clock.advance() == 20
    assert clock.time_ms == 20
    assert clock.time_seconds == 0.02


def test_clock_advance_custom_dt() -> None:
    clock = SimulationClock(tick_ms=10)
    assert clock.advance(5) == 5
    assert clock.advance(25) == 30
    assert clock.time_ms == 30


def test_clock_reset() -> None:
    clock = SimulationClock(tick_ms=10, start_time_ms=100)
    assert clock.time_ms == 100
    clock.advance()
    assert clock.time_ms == 110
    clock.reset()
    assert clock.time_ms == 0
    clock.reset(start_time_ms=500)
    assert clock.time_ms == 500


def test_clock_rejects_negative_advance() -> None:
    clock = SimulationClock()
    with pytest.raises(ValueError, match="Cannot advance clock by negative step"):
        clock.advance(-10)


def test_clock_rejects_invalid_init() -> None:
    with pytest.raises(ValueError, match="tick_ms must be positive"):
        SimulationClock(tick_ms=0)
    with pytest.raises(ValueError, match="start_time_ms must be non-negative"):
        SimulationClock(start_time_ms=-1)
