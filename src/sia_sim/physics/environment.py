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

    def __init__(
        self,
        base_tws_m_s: float,
        base_twa_deg: float,
        enable_turbulence: bool = False,
    ) -> None:
        self.base_tws_m_s = max(0.0, base_tws_m_s)
        self.base_twa_deg = base_twa_deg % 360.0
        self.enable_turbulence = enable_turbulence
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
        # Add deterministic organic natural wind turbulence (~4-8% fluctuation) if enabled
        if self.enable_turbulence and self.base_tws_m_s > 0.0:
            t_s = time_ms / 1000.0
            turb = (
                0.05 * math.sin(0.37 * t_s)
                + 0.03 * math.cos(0.83 * t_s + 1.2)
                + 0.02 * math.sin(1.71 * t_s + 2.5)
            )
            current_speed = max(0.0, current_speed * (1.0 + turb))
            dir_turb = 2.0 * math.sin(0.29 * t_s + 0.7) + 1.2 * math.cos(0.71 * t_s)
            dir_shift += dir_turb

        current_dir = (self.base_twa_deg + dir_shift) % 360.0
        return current_speed, current_dir


class WaveModel:
    """Deterministic deep-water linear wave kinematics model with continuous ambient field."""

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

    def evaluate_ambient_excitation(
        self,
        x_m: float,
        y_m: float,
        time_s: float,
        heading_deg: float,
        mass_kg: float = 4500.0,
    ) -> tuple[float, float, float, float]:
        """Calculates continuous ambient wave excitation for living sea background.

        Returns:
            (elevation_m, roll_moment_nm, pitch_moment_nm, vertical_accel_m_s2)
        """
        if self.wave_height_m <= 0.001:
            return 0.0, 0.0, 0.0, 0.0

        dir_rad = math.radians(self.wave_direction_deg)
        proj_dist = x_m * math.cos(dir_rad) + y_m * math.sin(dir_rad)
        phase = self.wave_number_k * proj_dist - self.angular_frequency_omega * time_s

        elevation = (self.wave_height_m / 2.0) * math.cos(phase)
        slope_mag = self.wave_number_k * (self.wave_height_m / 2.0) * math.sin(phase)

        # Relative wave angle to vessel heading (0: following, 90: beam, 180: head sea)
        rel_angle_rad = math.radians((heading_deg - self.wave_direction_deg) % 360.0)

        # Transverse and longitudinal wave slope components relative to hull
        transverse_slope = slope_mag * math.sin(rel_angle_rad)
        longitudinal_slope = slope_mag * math.cos(rel_angle_rad)

        # Froude-Krylov continuous excitation moments with GM approximations
        # (GM_T ~ 1.2m, GM_L ~ 10m)
        gm_t = 1.2
        gm_l = 10.0
        # Gentle background rolling moment coefficient
        smith_factor = 0.12
        roll_moment_nm = mass_kg * GRAVITY * gm_t * transverse_slope * smith_factor
        pitch_moment_nm = mass_kg * GRAVITY * gm_l * longitudinal_slope * 0.10 * smith_factor

        # Vertical wave surface acceleration d^2(eta)/dt^2
        vert_accel = -(self.angular_frequency_omega**2) * elevation

        return elevation, roll_moment_nm, pitch_moment_nm, vert_accel


class CurrentModel:
    """Sea current velocity model."""

    def __init__(self, current_speed_m_s: float = 0.0, current_direction_deg: float = 0.0) -> None:
        self.current_speed_m_s = max(0.0, current_speed_m_s)
        self.current_direction_deg = current_direction_deg % 360.0

    def evaluate(self) -> tuple[float, float]:
        return self.current_speed_m_s, self.current_direction_deg
