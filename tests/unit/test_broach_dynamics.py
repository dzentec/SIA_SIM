"""Broach precursor dynamics and physical stability verification tests (SIM-005)."""

from __future__ import annotations

from sia_sim.contracts.data import EnvironmentState
from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.world import WorldModel


class TestPhysicalStabilityInvariants:
    def test_roll_decay_to_upright_in_calm_water(self) -> None:
        """When released from heel in calm water with no wind, vessel rights itself."""
        cfg = VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heel_deg=20.0,
            initial_heading_deg=0.0,
            initial_sog_kt=0.0,
        )
        dyn = VesselDynamics.from_config(cfg)
        calm_env = EnvironmentState(
            true_wind_speed_m_s=0.0,
            true_wind_angle_deg=0.0,
            wave_height_m=0.0,
            wave_period_s=5.0,
            current_speed_m_s=0.0,
            current_direction_deg=0.0,
        )

        # Integrate for 8 seconds (800 ticks)
        for _ in range(800):
            state = dyn.step(0.01, calm_env)

        # Heel should have decayed towards 0 (upright equilibrium)
        assert abs(state.heel_deg) < 5.0
        assert abs(state.roll_rate_deg_s) < 2.0

    def test_terminal_speed_bounded_in_steady_wind(self) -> None:
        """Under steady 20 kt wind, displacement hull speed remains physically realistic."""
        cfg = VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heel_deg=10.0,
            initial_heading_deg=45.0,
            initial_sog_kt=2.0,
        )
        dyn = VesselDynamics.from_config(cfg)
        steady_env = EnvironmentState(
            true_wind_speed_m_s=10.3,  # 20 kt
            true_wind_angle_deg=90.0,  # Beam reach
            wave_height_m=1.0,
            wave_period_s=6.0,
            current_speed_m_s=0.0,
            current_direction_deg=0.0,
        )

        # Integrate for 15 seconds (1500 ticks)
        for _ in range(1500):
            state = dyn.step(0.01, steady_env)

        # Hull speed for 10.5m LOA is ~7-8 kt (3.6-4.1 m/s)
        assert 2.0 < state.sog_m_s < 5.0


class TestBroachPrecursorDynamics:
    def test_sim005_broach_precursor_sequence(self) -> None:
        """Verifies physical manifestation of the Broach Precursor (SIM-005 / BROACH_001):

        Timeline:
        T=0..10s: Steady sailing on beam/broad reach (heel ~15°, SOG ~5.8 kt).
        T=10s: Wave impact event occurs.
        T=12s: Heel escalates (>25°).
        T=13-15s: Rudder effectiveness drops, weather helm forces yaw turning into the wind.
        """
        scenario = Scenario(
            scenario_id="SIM-005",
            scenario_version="1.0.0",
            name="Broach Precursor Golden Scenario",
            description="IOR narrow stern monohull broach precursor dynamics test",
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
                        "impact_force_n": 10000.0,
                        "impact_roll_moment_nm": 20000.0,
                        "duration_ms": 2000,
                    },
                ),
                ScenarioEvent(
                    sim_time_ms=12000,
                    event_id="EVT-GUST-01",
                    event_type="wind_gust",
                    parameters={"tws_kt": 15.0, "duration_s": 4.0, "direction_shift_deg": 10.0},
                ),
            ),
            initial_tws_kt=20.0,
            initial_twa_deg=0.0,
            initial_wave_height_m=3.0,
            initial_wave_period_s=7.0,
        )

        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)
        dynamics = VesselDynamics.from_config(scenario.vessel)

        # Record metrics at key timestamps
        state_at_t9 = None
        state_at_t15 = None
        max_heel_during_event = 0.0

        for t_ms in range(0, scenario.duration_ms, 10):
            env = world.step(t_ms)
            wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)

            # Steer straight (rudder=0) or counter-rudder
            state = dynamics.step(
                dt_s=0.01,
                env=env,
                rudder_deg=0.0,
                mainsheet_pct=100.0,
                wave_impact_force_n=wave_f,
                wave_impact_roll_moment_nm=wave_rm,
                wave_impact_yaw_moment_nm=wave_ym,
            )

            if t_ms == 9000:
                state_at_t9 = state
            elif t_ms == 15000:
                state_at_t15 = state

            if 10000 <= t_ms <= 15000:
                max_heel_during_event = max(max_heel_during_event, abs(state.heel_deg))

        assert state_at_t9 is not None
        assert state_at_t15 is not None

        # 1. Before wave impact (T=9s): moderate heel
        assert abs(state_at_t9.heel_deg) < 30.0

        # 2. During wave impact / gust (T=10s..15s): heel escalates significantly
        assert max_heel_during_event > abs(state_at_t9.heel_deg)
        assert max_heel_during_event > 30.0

        # 3. Weather helm round-up into wind (T=15s): heading has turned significantly
        heading_delta = abs(state_at_t15.heading_deg - state_at_t9.heading_deg)
        assert heading_delta > 5.0 or abs(state_at_t15.yaw_rate_deg_s) > 1.0
