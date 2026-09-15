"""Unit tests for WorldModel ground-truth generation and scenario event execution."""

from __future__ import annotations

import math

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.physics.environment import KNOTS_TO_M_S
from sia_sim.physics.world import WorldModel


def sample_scenario() -> Scenario:
    return Scenario(
        scenario_id="SIM-005",
        scenario_version="1.0.0",
        name="Broach Precursor",
        description="Broach test",
        duration_ms=20000,
        seed=42,
        vessel=VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heel_deg=15.0,
            initial_heading_deg=65.0,
            initial_sog_kt=5.8,
        ),
        events=(
            ScenarioEvent(
                sim_time_ms=10000,
                event_id="EVT-WAVE-01",
                event_type="wave_impact",
                parameters={
                    "impact_force_n": 8000.0,
                    "impact_roll_moment_nm": 15000.0,
                    "duration_ms": 1500,
                },
            ),
            ScenarioEvent(
                sim_time_ms=12000,
                event_id="EVT-GUST-01",
                event_type="wind_gust",
                parameters={"tws_kt": 15.0, "duration_s": 4.0, "direction_shift_deg": 15.0},
            ),
        ),
        initial_tws_kt=20.0,
        initial_twa_deg=65.0,
        initial_wave_height_m=3.0,
        initial_wave_period_s=7.0,
    )


class TestWorldModel:
    def test_from_scenario_initial_state(self) -> None:
        scenario = sample_scenario()
        world = WorldModel.from_scenario(scenario)
        state = world.step(0)

        assert math.isclose(state.true_wind_speed_m_s, 20.0 * KNOTS_TO_M_S, rel_tol=1e-3)
        assert state.true_wind_angle_deg == 65.0
        assert state.wave_height_m == 3.0
        assert state.wave_period_s == 7.0

    def test_event_application_and_active_ids(self) -> None:
        scenario = sample_scenario()
        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)

        # Before any events
        assert world.get_active_event_ids(5000) == ()

        # During wave impact (10000 to 11500ms)
        active_at_10500 = world.get_active_event_ids(10500)
        assert "EVT-WAVE-01" in active_at_10500

        # During wind gust (12000 to 16000ms)
        active_at_14000 = world.get_active_event_ids(14000)
        assert "EVT-GUST-01" in active_at_14000

        # Wind speed increased during gust
        state_gust = world.step(14000)
        base_speed = 20.0 * KNOTS_TO_M_S
        assert state_gust.true_wind_speed_m_s > base_speed

    def test_bit_for_bit_determinism(self) -> None:
        scenario = sample_scenario()

        world1 = WorldModel.from_scenario(scenario)
        world1.apply_events(scenario.events)

        world2 = WorldModel.from_scenario(scenario)
        world2.apply_events(scenario.events)

        for t_ms in range(0, 20000, 10):  # 100 Hz ticks
            s1 = world1.step(t_ms)
            s2 = world2.step(t_ms)
            assert s1 == s2
