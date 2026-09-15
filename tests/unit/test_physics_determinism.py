"""Determinism verification tests for the physics and world model engine."""

from __future__ import annotations

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.world import WorldModel


def create_test_scenario(seed: int = 42) -> Scenario:
    return Scenario(
        scenario_id="SIM-005-DET",
        scenario_version="1.0.0",
        name="Determinism Test Scenario",
        description="Verify bit-for-bit repeatability across multiple simulation runs",
        duration_ms=10000,
        seed=seed,
        vessel=VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heel_deg=10.0,
            initial_heading_deg=65.0,
            initial_sog_kt=5.5,
        ),
        events=(
            ScenarioEvent(
                sim_time_ms=3000,
                event_id="EVT-WAVE-01",
                event_type="wave_impact",
                parameters={
                    "impact_force_n": 7500.0,
                    "impact_roll_moment_nm": 14000.0,
                    "duration_ms": 1500,
                },
            ),
            ScenarioEvent(
                sim_time_ms=5000,
                event_id="EVT-GUST-01",
                event_type="wind_gust",
                parameters={"tws_kt": 12.0, "duration_s": 3.0, "direction_shift_deg": 10.0},
            ),
        ),
        initial_tws_kt=20.0,
        initial_twa_deg=65.0,
        initial_wave_height_m=2.5,
        initial_wave_period_s=6.5,
    )


def run_simulation(scenario: Scenario) -> list[tuple[float, float, float, float, float]]:
    world = WorldModel.from_scenario(scenario)
    world.apply_events(scenario.events)
    dynamics = VesselDynamics.from_config(scenario.vessel)

    dt_s = 0.01  # 100 Hz
    trajectory: list[tuple[float, float, float, float, float]] = []

    for t_ms in range(0, scenario.duration_ms, 10):
        env_state = world.step(t_ms)
        wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)

        vessel_state = dynamics.step(
            dt_s=dt_s,
            env=env_state,
            rudder_deg=2.0 if t_ms > 4000 else 0.0,
            mainsheet_pct=100.0,
            wave_impact_force_n=wave_f,
            wave_impact_roll_moment_nm=wave_rm,
            wave_impact_yaw_moment_nm=wave_ym,
        )

        trajectory.append(
            (
                vessel_state.x_m,
                vessel_state.y_m,
                vessel_state.heading_deg,
                vessel_state.sog_m_s,
                vessel_state.heel_deg,
            )
        )

    return trajectory


class TestPhysicsDeterminism:
    def test_identical_runs_produce_bit_identical_trajectories(self) -> None:
        scenario = create_test_scenario(seed=42)

        run1 = run_simulation(scenario)
        run2 = run_simulation(scenario)

        assert len(run1) == 1000  # 10.0 s at 100 Hz
        assert len(run2) == 1000

        # Exact bit-for-bit equality check across all 1000 ticks
        for i, (state1, state2) in enumerate(zip(run1, run2, strict=True)):
            assert state1 == state2, f"Divergence detected at tick {i} (T={i * 10}ms)"

    def test_reset_and_rerun_produces_identical_trajectory(self) -> None:
        scenario = create_test_scenario(seed=100)

        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)
        dynamics = VesselDynamics.from_config(scenario.vessel)

        # First run
        traj1 = []
        for t_ms in range(0, 3000, 10):
            env = world.step(t_ms)
            state = dynamics.step(0.01, env)
            traj1.append((state.x_m, state.y_m, state.heading_deg))

        # Reset dynamics and world model
        dynamics.reset()
        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)

        # Second run
        traj2 = []
        for t_ms in range(0, 3000, 10):
            env = world.step(t_ms)
            state = dynamics.step(0.01, env)
            traj2.append((state.x_m, state.y_m, state.heading_deg))

        assert traj1 == traj2
