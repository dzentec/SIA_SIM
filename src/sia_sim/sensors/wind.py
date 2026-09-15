"""Wind sensor (anemometer / wind vane) simulation model."""

from __future__ import annotations

import math

import numpy as np

from sia_sim.contracts.data import EnvironmentState, VesselState, WindReading
from sia_sim.physics.forces import apparent_wind
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig

MPS_TO_KNOTS = 1.943844


class WindSensorModel:
    """Simulates masthead ultrasonic or mechanical wind vane & anemometer."""

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        speed_config: DegradationConfig | None = None,
        angle_config: DegradationConfig | None = None,
    ) -> None:
        self.rng = rng or np.random.default_rng(0)

        self.degrader_aws = ChannelDegrader(
            speed_config
            or DegradationConfig(
                noise_std=0.3,  # ~0.3 kt noise
                min_value=0.0,
            ),
            self.rng,
        )
        self.degrader_awa = ChannelDegrader(
            angle_config
            or DegradationConfig(
                noise_std=0.8,  # ~0.8 deg noise
            ),
            self.rng,
        )

        self._hardware_fault = False
        self._frozen = False

    def reset(self, rng: np.random.Generator | None = None) -> None:
        if rng is not None:
            self.rng = rng
        self.degrader_aws.reset(self.rng)
        self.degrader_awa.reset(self.rng)
        self._hardware_fault = False
        self._frozen = False

    def set_fault(self, fault: bool) -> None:
        self._hardware_fault = fault

    def set_frozen(self, frozen: bool) -> None:
        self._frozen = frozen

    def generate(
        self,
        env: EnvironmentState,
        vessel: VesselState,
        sim_time_ms: int,
        fault_override: bool = False,
        freeze_override: bool = False,
    ) -> WindReading:
        """Transform physical true wind and vessel velocity into degraded WindReading."""
        is_fault = self._hardware_fault or fault_override
        is_freeze = self._frozen or freeze_override

        if is_fault:
            return WindReading(
                apparent_wind_speed_kt=None,
                apparent_wind_angle_deg=None,
                fault=True,
            )

        # Decompose body velocities
        heading_rad = math.radians(vessel.heading_deg)
        cog_rad = math.radians(vessel.cog_deg)
        drift_rad = cog_rad - heading_rad

        u_m_s = vessel.sog_m_s * math.cos(drift_rad)
        v_m_s = vessel.sog_m_s * math.sin(drift_rad)

        raw_aws_m_s, raw_awa_deg = apparent_wind(
            u_m_s=u_m_s,
            v_m_s=v_m_s,
            heading_deg=vessel.heading_deg,
            tws_m_s=env.true_wind_speed_m_s,
            twa_deg=env.true_wind_angle_deg,
        )

        # Mast motion roll rate induced velocity distortion
        # Mast height ~14m, CE ~5.6m. Roll velocity at masthead = 14 * p_rad_s
        p_rad_s = math.radians(vessel.roll_rate_deg_s)
        mast_roll_vel = 14.0 * p_rad_s * 0.3  # Damped mast motion contribution

        aws_raw_kt = raw_aws_m_s * MPS_TO_KNOTS
        awa_raw_deg = raw_awa_deg + math.degrees(math.atan2(mast_roll_vel, max(1.0, raw_aws_m_s)))

        # Normalize AWA to [-180, +180]
        if awa_raw_deg > 180.0:
            awa_raw_deg -= 360.0
        elif awa_raw_deg < -180.0:
            awa_raw_deg += 360.0

        aws_kt = self.degrader_aws.process(aws_raw_kt, sim_time_ms, is_fault, is_freeze)
        awa_deg = self.degrader_awa.process(awa_raw_deg, sim_time_ms, is_fault, is_freeze)

        # Re-normalize degraded AWA
        if awa_deg is not None:
            if awa_deg > 180.0:
                awa_deg -= 360.0
            elif awa_deg < -180.0:
                awa_deg += 360.0

        return WindReading(
            apparent_wind_speed_kt=aws_kt,
            apparent_wind_angle_deg=awa_deg,
            fault=is_fault or (aws_kt is None and awa_deg is None),
        )
