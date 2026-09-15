"""IMU sensor simulation model with multi-axis degradation."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from sia_sim.contracts.data import IMUReading, VesselState
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig

if TYPE_CHECKING:
    pass

GRAVITY = 9.80665  # m/s^2


class IMUSensorModel:
    """Simulates 6-DOF / 9-DOF Inertial Measurement Unit with noise, bias, drift, and faults."""

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        roll_config: DegradationConfig | None = None,
        pitch_config: DegradationConfig | None = None,
        roll_rate_config: DegradationConfig | None = None,
        pitch_rate_config: DegradationConfig | None = None,
        yaw_rate_config: DegradationConfig | None = None,
        accel_config: DegradationConfig | None = None,
    ) -> None:
        self.rng = rng or np.random.default_rng(0)

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

    def set_fault(self, fault: bool) -> None:
        self._hardware_fault = fault

    def set_frozen(self, frozen: bool) -> None:
        self._frozen = frozen

    def generate(
        self,
        vessel: VesselState,
        sim_time_ms: int,
        fault_override: bool = False,
        freeze_override: bool = False,
    ) -> IMUReading:
        """Transform true physical vessel state into degraded IMUReading."""
        is_fault = self._hardware_fault or fault_override
        is_freeze = self._frozen or freeze_override

        phi_rad = math.radians(vessel.heel_deg)
        theta_rad = math.radians(vessel.pitch_deg)

        # Gravitational specific force in body frame
        raw_ax = -GRAVITY * math.sin(theta_rad)
        raw_ay = GRAVITY * math.sin(phi_rad) * math.cos(theta_rad)
        raw_az = GRAVITY * math.cos(phi_rad) * math.cos(theta_rad)

        roll = self.degrader_roll.process(vessel.heel_deg, sim_time_ms, is_fault, is_freeze)
        pitch = self.degrader_pitch.process(vessel.pitch_deg, sim_time_ms, is_fault, is_freeze)
        roll_rate = self.degrader_roll_rate.process(
            vessel.roll_rate_deg_s, sim_time_ms, is_fault, is_freeze
        )
        pitch_rate = self.degrader_pitch_rate.process(0.0, sim_time_ms, is_fault, is_freeze)
        yaw_rate = self.degrader_yaw_rate.process(
            vessel.yaw_rate_deg_s, sim_time_ms, is_fault, is_freeze
        )

        acc_x = self.degrader_acc_x.process(raw_ax, sim_time_ms, is_fault, is_freeze)
        acc_y = self.degrader_acc_y.process(raw_ay, sim_time_ms, is_fault, is_freeze)
        acc_z = self.degrader_acc_z.process(raw_az, sim_time_ms, is_fault, is_freeze)

        has_fault = is_fault or (roll is None and roll_rate is None and yaw_rate is None)

        return IMUReading(
            roll_deg=roll,
            pitch_deg=pitch,
            roll_rate_deg_s=roll_rate,
            pitch_rate_deg_s=pitch_rate,
            yaw_rate_deg_s=yaw_rate,
            accel_x_m_s2=acc_x,
            accel_y_m_s2=acc_y,
            accel_z_m_s2=acc_z,
            fault=has_fault,
        )
