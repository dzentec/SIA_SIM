"""Deterministic fixed-step numerical integration algorithms."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def rk4_step(
    state: np.ndarray,
    derivatives_fn: Callable[[np.ndarray, float], np.ndarray],
    dt: float,
    t: float = 0.0,
) -> np.ndarray:
    """Perform a single deterministic 4th-order Runge-Kutta integration step.

    Parameters:
      state: Current state vector array [N].
      derivatives_fn: Callable(state, t) -> dstate_dt [N].
      dt: Fixed time step in seconds (e.g. 0.01 s for 100 Hz).
      t: Current simulation time in seconds.

    Returns:
      New state vector array [N] at time t + dt.
    """
    k1 = derivatives_fn(state, t)
    k2 = derivatives_fn(state + 0.5 * dt * k1, t + 0.5 * dt)
    k3 = derivatives_fn(state + 0.5 * dt * k2, t + 0.5 * dt)
    k4 = derivatives_fn(state + dt * k3, t + dt)

    result = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return np.asarray(result, dtype=np.float64)
