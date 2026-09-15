"""Deterministic signal degradation primitives (noise, bias, drift, latency, dropout, freeze)."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DegradationConfig:
    """Configuration for sensor signal degradation."""

    noise_std: float = 0.0
    """Gaussian noise standard deviation sigma (in signal units)."""

    bias: float = 0.0
    """Constant static bias offset added to measurement."""

    drift_rate: float = 0.0
    """Time-varying drift rate (units per second): bias(t) = bias + drift_rate * (t_ms / 1000)."""

    latency_ms: int = 0
    """Measurement transport/processing delay in milliseconds (quantized to 10 ms ticks)."""

    dropout_prob: float = 0.0
    """Probability per tick [0.0, 1.0] of signal dropout (emitting None)."""

    min_value: float | None = None
    """Physical lower sensor bound. Values outside are marked invalid or clamped."""

    max_value: float | None = None
    """Physical upper sensor bound. Values outside are marked invalid or clamped."""


class ChannelDegrader:
    """Stateful deterministic signal degrader for a single scalar measurement channel.

    Applies:
    1. Input validation & physical bounding.
    2. Additive static bias and linear time drift.
    3. Gaussian noise sampled from an isolated PRNG generator.
    4. Deterministic latency FIFO buffer.
    5. Frozen sensor behavior (holding previous output constant).
    6. Dropout fault (emitting None with strict null semantics).
    """

    def __init__(
        self,
        config: DegradationConfig | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.config = config or DegradationConfig()
        self.rng = rng or np.random.default_rng(0)
        self._buffer_len = max(0, self.config.latency_ms // 10)
        self._buffer: deque[float | None] = deque()
        self._last_output: float | None = None
        self._frozen_value: float | None = None
        self._is_frozen = False
        self._is_faulted = False

    def reset(self, rng: np.random.Generator | None = None) -> None:
        """Reset internal buffers, frozen states, and optionally RNG generator."""
        if rng is not None:
            self.rng = rng
        self._buffer.clear()
        self._last_output = None
        self._frozen_value = None
        self._is_frozen = False
        self._is_faulted = False

    def set_frozen(self, frozen: bool) -> None:
        """Manually toggle frozen sensor state."""
        self._is_frozen = frozen
        if not frozen:
            self._frozen_value = None

    def set_faulted(self, faulted: bool) -> None:
        """Manually toggle sensor fault state (causing dropouts / None)."""
        self._is_faulted = faulted

    def process(
        self,
        raw_value: float | None,
        sim_time_ms: int,
        fault_override: bool = False,
        freeze_override: bool = False,
    ) -> float | None:
        """Degrade a raw scalar measurement according to configuration and active faults."""
        # 1. Total fault check (signal absence or hardware fault)
        if raw_value is None or self._is_faulted or fault_override:
            output = None
        else:
            # Check random dropout
            if self.config.dropout_prob > 0.0 and self.rng.random() < self.config.dropout_prob:
                output = None
            else:
                # 2. Additive bias & linear drift
                t_s = sim_time_ms / 1000.0
                current_bias = self.config.bias + self.config.drift_rate * t_s
                degraded = float(raw_value + current_bias)

                # 3. Gaussian noise
                if self.config.noise_std > 0.0:
                    noise = float(self.rng.normal(0.0, self.config.noise_std))
                    degraded += noise

                # 4. Out-of-bounds check (if sensor rails / clips)
                if self.config.min_value is not None:
                    degraded = max(self.config.min_value, degraded)
                if self.config.max_value is not None:
                    degraded = min(self.config.max_value, degraded)

                output = degraded

        # 5. Latency queue
        if self._buffer_len > 0:
            self._buffer.append(output)
            if len(self._buffer) <= self._buffer_len:
                # Buffer filling up: output initial None or first valid
                delayed_output = None
            else:
                delayed_output = self._buffer.popleft()
        else:
            delayed_output = output

        # 6. Frozen sensor fault handling
        is_frozen = self._is_frozen or freeze_override
        if is_frozen:
            if self._frozen_value is None:
                self._frozen_value = (
                    delayed_output if delayed_output is not None else self._last_output
                )
            result = self._frozen_value
        else:
            self._frozen_value = None
            result = delayed_output

        if result is not None and not math.isnan(result):
            self._last_output = result

        return result
