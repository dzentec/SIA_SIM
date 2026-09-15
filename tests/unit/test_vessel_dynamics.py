"""Unit tests for VesselDynamics numerical integration and trajectory calculations."""

from __future__ import annotations

import math

from sia_sim.contracts.data import EnvironmentState
from sia_sim.contracts.scenario import VesselConfig
from sia_sim.physics.dynamics import VesselDynamics


def sample_vessel_config() -> VesselConfig:
    return VesselConfig(
        vessel_type="monohull_ior",
        loa_m=10.5,
        beam_m=3.2,
        displacement_kg=4500.0,
        initial_heel_deg=0.0,
        initial_heading_deg=45.0,
        initial_sog_kt=5.0,
    )


def sample_environment() -> EnvironmentState:
    return EnvironmentState(
        true_wind_speed_m_s=10.0,  # ~19.4 kt
        true_wind_angle_deg=90.0,  # Beam reach
        wave_height_m=1.0,
        wave_period_s=5.0,
        current_speed_m_s=0.0,
        current_direction_deg=0.0,
    )


class TestVesselDynamics:
    def test_initial_state_matches_config(self) -> None:
        cfg = sample_vessel_config()
        dyn = VesselDynamics.from_config(cfg)
        env = sample_environment()

        state = dyn.step(0.01, env)
        assert math.isclose(state.heading_deg, 45.0, abs_tol=1.0)
        assert state.sog_m_s > 2.0

    def test_beam_reach_develops_heel_and_speed(self) -> None:
        cfg = sample_vessel_config()
        dyn = VesselDynamics.from_config(cfg)
        env = sample_environment()

        # Step 500 ticks = 5 seconds
        for _ in range(500):
            state = dyn.step(0.01, env, rudder_deg=0.0)

        # Vessel should be moving forward and heeled
        assert state.sog_m_s > 2.0
        assert state.heel_deg != 0.0

    def test_rudder_commands_steer_vessel(self) -> None:
        cfg = sample_vessel_config()
        dyn = VesselDynamics.from_config(cfg)
        env = sample_environment()

        # Apply starboard rudder (+5 deg) for 3 seconds
        for _ in range(300):
            state = dyn.step(0.01, env, rudder_deg=5.0)

        # Yaw rate should be non-zero
        assert state.yaw_rate_deg_s != 0.0

    def test_reset_restores_initial_state(self) -> None:
        cfg = sample_vessel_config()
        dyn = VesselDynamics.from_config(cfg)
        env = sample_environment()

        for _ in range(200):
            dyn.step(0.01, env, rudder_deg=10.0)

        dyn.reset()
        state = dyn.step(0.001, env)
        assert math.isclose(state.heading_deg, 45.0, abs_tol=0.1)
