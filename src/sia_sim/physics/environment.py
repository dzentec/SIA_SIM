"""Deterministic environmental physics models (wind, waves, current).

Provides causal calculations for:
- Mean wind field with smooth half-cosine deterministic gust envelopes.
- Deep-water linear wave kinematics (elevation, encounter frequency, orbital velocities).
- Sea current velocity vectors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

GRAVITY = 9.80665  # m/s² standard gravitational acceleration
KNOTS_TO_M_S = 0.5144444444444445
M_S_TO_KNOTS = 1.0 / KNOTS_TO_M_S


@dataclass(frozen=True)
class ActiveGust:
    """An active deterministic wind gust envelope."""

    event_id: str
    start_time_ms: int
    duration_ms: int
    peak_speed_increase_m_s: float
    direction_shift_deg: float = 0.0

    def evaluate(self, current_time_ms: int) -> tuple[float, float]:
        """Evaluate extra wind speed (m/s) and direction shift (deg) at current_time_ms."""
        if current_time_ms < self.start_time_ms:
            return 0.0, 0.0
        elapsed = current_time_ms - self.start_time_ms
        if elapsed >= self.duration_ms:
            return 0.0, 0.0

        # Smooth 1 - cos(2*pi*t/T) envelope
        fraction = elapsed / self.duration_ms
        envelope = 0.5 * (1.0 - math.cos(2.0 * math.pi * fraction))
        speed_delta = self.peak_speed_increase_m_s * envelope
        dir_delta = self.direction_shift_deg * envelope
        return speed_delta, dir_delta

    def is_expired(self, current_time_ms: int) -> bool:
        return current_time_ms >= (self.start_time_ms + self.duration_ms)


@dataclass(frozen=True)
class ActiveWaveImpact:
    """An active deterministic wave impact / slamming event."""

    event_id: str
    impact_time_ms: int
    duration_ms: int
    impact_force_n: float
    impact_roll_moment_nm: float
    impact_yaw_moment_nm: float = 0.0

    def evaluate(self, current_time_ms: int) -> tuple[float, float, float]:
        """Evaluate impact force (N), roll moment (Nm), and yaw moment (Nm) at current_time_ms."""
        if current_time_ms < self.impact_time_ms:
            return 0.0, 0.0, 0.0
        elapsed = current_time_ms - self.impact_time_ms
        if elapsed >= self.duration_ms:
            return 0.0, 0.0, 0.0

        # Rapid exponential rise and decay envelope
        t_norm = elapsed / self.duration_ms
        # Peak at ~15% of duration
        envelope = (t_norm / 0.15) * math.exp(1.0 - (t_norm / 0.15)) if t_norm > 0 else 0.0
        envelope = min(max(envelope, 0.0), 2.0) / 2.0  # Normalized peak approx 1.0

        yaw_moment = (
            self.impact_yaw_moment_nm
            if self.impact_yaw_moment_nm != 0.0
            else -0.35 * self.impact_roll_moment_nm
        )

        return (
            self.impact_force_n * envelope,
            self.impact_roll_moment_nm * envelope,
            yaw_moment * envelope,
        )

    def is_expired(self, current_time_ms: int) -> bool:
        return current_time_ms >= (self.impact_time_ms + self.duration_ms)


class WindModel:
    """Causal wind model computing true wind speed and direction."""

    def __init__(self, base_tws_m_s: float, base_twa_deg: float) -> None:
        self.base_tws_m_s = max(0.0, base_tws_m_s)
        self.base_twa_deg = base_twa_deg % 360.0
        self._gusts: list[ActiveGust] = []

    def add_gust(self, gust: ActiveGust) -> None:
        self._gusts.append(gust)

    def evaluate(self, time_ms: int) -> tuple[float, float]:
        """Returns (true_wind_speed_m_s, true_wind_angle_deg) at time_ms."""
        speed_extra = 0.0
        dir_shift = 0.0

        # Clean expired gusts while evaluating
        active = []
        for gust in self._gusts:
            if not gust.is_expired(time_ms):
                active.append(gust)
                s, d = gust.evaluate(time_ms)
                speed_extra += s
                dir_shift += d
        self._gusts = active

        current_speed = max(0.0, self.base_tws_m_s + speed_extra)
        current_dir = (self.base_twa_deg + dir_shift) % 360.0
        return current_speed, current_dir


class WaveModel:
    """Deterministic deep-water linear wave kinematics model."""

    def __init__(
        self,
        wave_height_m: float,
        wave_period_s: float,
        wave_direction_deg: float = 0.0,
    ) -> None:
        self.wave_height_m = max(0.0, wave_height_m)
        self.wave_period_s = max(0.1, wave_period_s)
        self.wave_direction_deg = wave_direction_deg % 360.0
        self._impacts: list[ActiveWaveImpact] = []

        # Deep-water dispersion relation: lambda = g * T^2 / (2 * pi)
        self.wavelength_m = (GRAVITY * (self.wave_period_s**2)) / (2.0 * math.pi)
        self.wave_number_k = (2.0 * math.pi) / self.wavelength_m
        self.angular_frequency_omega = (2.0 * math.pi) / self.wave_period_s
        self.max_wave_slope_rad = self.wave_number_k * (self.wave_height_m / 2.0)

    def add_impact(self, impact: ActiveWaveImpact) -> None:
        self._impacts.append(impact)

    def evaluate_impact(self, time_ms: int) -> tuple[float, float, float]:
        """Returns active (force_n, roll_moment_nm, yaw_moment_nm) from wave impact events."""
        total_force = 0.0
        total_roll_moment = 0.0
        total_yaw_moment = 0.0
        active = []
        for impact in self._impacts:
            if not impact.is_expired(time_ms):
                active.append(impact)
                f, rm, ym = impact.evaluate(time_ms)
                total_force += f
                total_roll_moment += rm
                total_yaw_moment += ym
        self._impacts = active
        return total_force, total_roll_moment, total_yaw_moment

    def wave_elevation(self, x_m: float, y_m: float, time_s: float) -> float:
        """Linear wave elevation eta at position (x, y) and time t."""
        if self.wave_height_m <= 0.0:
            return 0.0
        dir_rad = math.radians(self.wave_direction_deg)
        proj_dist = x_m * math.cos(dir_rad) + y_m * math.sin(dir_rad)
        phase = self.wave_number_k * proj_dist - self.angular_frequency_omega * time_s
        return (self.wave_height_m / 2.0) * math.cos(phase)


class CurrentModel:
    """Sea current velocity model."""

    def __init__(self, current_speed_m_s: float = 0.0, current_direction_deg: float = 0.0) -> None:
        self.current_speed_m_s = max(0.0, current_speed_m_s)
        self.current_direction_deg = current_direction_deg % 360.0

    def evaluate(self) -> tuple[float, float]:
        return self.current_speed_m_s, self.current_direction_deg
