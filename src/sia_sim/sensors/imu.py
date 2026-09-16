"""IMU sensor simulation model with multi-axis degradation."""

from __future__ import annotations

import math

import numpy as np

from sia_sim.contracts.data import IMUReading, VesselState
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig

GRAVITY = 9.80665  # m/s^2


class IMUSensorModel:
    """Simulates 6-DOF / 9-DOF Inertial Measurement Unit with noise, bias, drift, faults,

    and RFC v1.1 Edge Peak Computing & Digital Low-Pass Filter (LPF).
    """

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        sample_rate_hz: int = 100,
        lpf_cutoff_hz: float = 20.0,
        roll_config: DegradationConfig | None = None,
        pitch_config: DegradationConfig | None = None,
        roll_rate_config: DegradationConfig | None = None,
        pitch_rate_config: DegradationConfig | None = None,
        yaw_rate_config: DegradationConfig | None = None,
        accel_config: DegradationConfig | None = None,
    ) -> None:
        self.rng = rng or np.random.default_rng(0)
        self.sample_rate_hz = sample_rate_hz
        self.lpf_cutoff_hz = lpf_cutoff_hz

        # Default realistic MEMS IMU noise profiles if none provided
        self.degrader_roll = ChannelDegrader(
            roll_config or DegradationConfig(noise_std=0.1), self.rng
        )
        self.degrader_pitch = ChannelDegrader(
            pitch_config or DegradationConfig(noise_std=0.1), self.rng
        )
        self.degrader_roll_rate = ChannelDegrader(
            roll_rate_config or DegradationConfig(noise_std=0.2), self.rng
        )
        self.degrader_pitch_rate = ChannelDegrader(
            pitch_rate_config or DegradationConfig(noise_std=0.2), self.rng
        )
        self.degrader_yaw_rate = ChannelDegrader(
            yaw_rate_config or DegradationConfig(noise_std=0.2), self.rng
        )

        acc_cfg = accel_config or DegradationConfig(noise_std=0.05)
        self.degrader_acc_x = ChannelDegrader(acc_cfg, self.rng)
        self.degrader_acc_y = ChannelDegrader(acc_cfg, self.rng)
        self.degrader_acc_z = ChannelDegrader(acc_cfg, self.rng)

        self._hardware_fault = False
        self._frozen = False

        # Internal MCU 100 Hz State & Digital Low Pass Filter
        self._lpf_roll: float | None = None
        self._lpf_pitch: float | None = None
        self._lpf_roll_rate: float | None = None
        self._lpf_yaw_rate: float | None = None
        self._lpf_acc_x: float | None = None
        self._lpf_acc_y: float | None = None
        self._lpf_acc_z: float | None = None

        # Sample and hold for decimated output rate
        self._last_sample_time_ms = -1000
        self._last_reading: IMUReading | None = None

        # Edge Peak Envelope (MOD-01) ring buffer tracking
        self._peak_accel_g = 1.0
        self._peak_roll_rate_deg_s = 0.0

    def reset(self, rng: np.random.Generator | None = None) -> None:
        if rng is not None:
            self.rng = rng
        self.degrader_roll.reset(self.rng)
        self.degrader_pitch.reset(self.rng)
        self.degrader_roll_rate.reset(self.rng)
        self.degrader_pitch_rate.reset(self.rng)
        self.degrader_yaw_rate.reset(self.rng)
        self.degrader_acc_x.reset(self.rng)
        self.degrader_acc_y.reset(self.rng)
        self.degrader_acc_z.reset(self.rng)
        self._hardware_fault = False
        self._frozen = False

        self._lpf_roll = None
        self._lpf_pitch = None
        self._lpf_roll_rate = None
        self._lpf_yaw_rate = None
        self._lpf_acc_x = None
        self._lpf_acc_y = None
        self._lpf_acc_z = None
        self._last_sample_time_ms = -1000
        self._last_reading = None
        self._peak_accel_g = 1.0
        self._peak_roll_rate_deg_s = 0.0

    def set_fault(self, fault: bool) -> None:
        self._hardware_fault = fault

    def set_frozen(self, frozen: bool) -> None:
        self._frozen = frozen

    def _apply_lpf(
        self, prev: float | None, current: float | None, dt_s: float = 0.01
    ) -> float | None:
        if current is None:
            return None
        if prev is None:
            return current
        if self.lpf_cutoff_hz <= 0.0:
            return current
        # First-order IIR LPF filter coefficient alpha = 2*pi*fc*dt / (1 + 2*pi*fc*dt)
        rc = 1.0 / (2.0 * math.pi * self.lpf_cutoff_hz)
        alpha = dt_s / (rc + dt_s)
        return prev + alpha * (current - prev)

    def generate(
        self,
        vessel: VesselState,
        sim_time_ms: int,
        fault_override: bool = False,
        freeze_override: bool = False,
    ) -> IMUReading:
        """Transform true physical vessel state into degraded IMUReading with LPF and sampling."""
        is_fault = self._hardware_fault or fault_override
        is_freeze = self._frozen or freeze_override

        # 1. Check decimation interval (Sample & Hold)
        sample_interval_ms = int(1000 / max(1, min(100, self.sample_rate_hz)))
        should_sample = (
            self._last_reading is None
            or (sim_time_ms - self._last_sample_time_ms) >= sample_interval_ms
            or is_fault != self._last_reading.fault
        )

        phi_rad = math.radians(vessel.heel_deg)
        theta_rad = math.radians(vessel.pitch_deg)

        # Gravitational specific force in body frame
        raw_ax = -GRAVITY * math.sin(theta_rad)
        raw_ay = GRAVITY * math.sin(phi_rad) * math.cos(theta_rad)
        raw_az = GRAVITY * math.cos(phi_rad) * math.cos(theta_rad)

        raw_roll = self.degrader_roll.process(vessel.heel_deg, sim_time_ms, is_fault, is_freeze)
        raw_pitch = self.degrader_pitch.process(vessel.pitch_deg, sim_time_ms, is_fault, is_freeze)
        raw_roll_rate = self.degrader_roll_rate.process(
            vessel.roll_rate_deg_s, sim_time_ms, is_fault, is_freeze
        )
        raw_pitch_rate = self.degrader_pitch_rate.process(0.0, sim_time_ms, is_fault, is_freeze)
        raw_yaw_rate = self.degrader_yaw_rate.process(
            vessel.yaw_rate_deg_s, sim_time_ms, is_fault, is_freeze
        )

        raw_acc_x = self.degrader_acc_x.process(raw_ax, sim_time_ms, is_fault, is_freeze)
        raw_acc_y = self.degrader_acc_y.process(raw_ay, sim_time_ms, is_fault, is_freeze)
        raw_acc_z = self.degrader_acc_z.process(raw_az, sim_time_ms, is_fault, is_freeze)

        if is_freeze:
            roll_out = raw_roll
            pitch_out = raw_pitch
            roll_rate_out = raw_roll_rate
            yaw_rate_out = raw_yaw_rate
            acc_x_out = raw_acc_x
            acc_y_out = raw_acc_y
            acc_z_out = raw_acc_z
        else:
            # 2. Internal MCU 100 Hz Digital Low-Pass Filter (MOD-03)
            self._lpf_roll = self._apply_lpf(self._lpf_roll, raw_roll)
            self._lpf_pitch = self._apply_lpf(self._lpf_pitch, raw_pitch)
            self._lpf_roll_rate = self._apply_lpf(self._lpf_roll_rate, raw_roll_rate)
            self._lpf_yaw_rate = self._apply_lpf(self._lpf_yaw_rate, raw_yaw_rate)
            self._lpf_acc_x = self._apply_lpf(self._lpf_acc_x, raw_acc_x)
            self._lpf_acc_y = self._apply_lpf(self._lpf_acc_y, raw_acc_y)
            self._lpf_acc_z = self._apply_lpf(self._lpf_acc_z, raw_acc_z)
            roll_out = self._lpf_roll
            pitch_out = self._lpf_pitch
            roll_rate_out = self._lpf_roll_rate
            yaw_rate_out = self._lpf_yaw_rate
            acc_x_out = self._lpf_acc_x
            acc_y_out = self._lpf_acc_y
            acc_z_out = self._lpf_acc_z

        # 3. Peak Envelope Edge Accumulator (MOD-01)
        if raw_acc_z is not None:
            g_mag = (
                math.sqrt(
                    (raw_acc_x or 0.0) ** 2 + (raw_acc_y or 0.0) ** 2 + (raw_acc_z or 0.0) ** 2
                )
                / GRAVITY
            )
            self._peak_accel_g = max(self._peak_accel_g, g_mag)
        if raw_roll_rate is not None:
            self._peak_roll_rate_deg_s = max(self._peak_roll_rate_deg_s, abs(raw_roll_rate))

        has_fault = is_fault or (
            roll_out is None and roll_rate_out is None and yaw_rate_out is None
        )

        if should_sample:
            self._last_sample_time_ms = sim_time_ms
            self._last_reading = IMUReading(
                roll_deg=roll_out,
                pitch_deg=pitch_out,
                roll_rate_deg_s=roll_rate_out,
                pitch_rate_deg_s=raw_pitch_rate,
                yaw_rate_deg_s=yaw_rate_out,
                accel_x_m_s2=acc_x_out,
                accel_y_m_s2=acc_y_out,
                accel_z_m_s2=acc_z_out,
                fault=has_fault,
            )

        return (
            self._last_reading
            if self._last_reading is not None
            else IMUReading(
                roll_deg=roll_out,
                pitch_deg=pitch_out,
                roll_rate_deg_s=roll_rate_out,
                pitch_rate_deg_s=raw_pitch_rate,
                yaw_rate_deg_s=yaw_rate_out,
                accel_x_m_s2=acc_x_out,
                accel_y_m_s2=acc_y_out,
                accel_z_m_s2=acc_z_out,
                fault=has_fault,
            )
        )
