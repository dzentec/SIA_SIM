"""Demonstration script: Run SIM-005 Broach Precursor simulation and display vessel trajectory."""

from __future__ import annotations

import math
import sys

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.forces import apparent_wind
from sia_sim.physics.world import WorldModel

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def create_sim005_scenario() -> Scenario:
    """Constructs the reference SIM-005 Broach Precursor scenario."""
    return Scenario(
        scenario_id="SIM-005",
        scenario_version="1.0.0",
        name="Broach Precursor Golden Scenario",
        description="IOR narrow stern monohull broach precursor dynamics (100 Hz)",
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


def main() -> None:
    scenario = create_sim005_scenario()
    world = WorldModel.from_scenario(scenario)
    world.apply_events(scenario.events)
    dynamics = VesselDynamics.from_config(scenario.vessel)

    print("\n" + "=" * 96)
    print(f"  SIA SIMULATION - SCENARIO TRAJECTORY DEMO: {scenario.name} ({scenario.scenario_id})")
    vessel_desc = (
        f"  Vessel: {scenario.vessel.vessel_type} | "
        f"LOA: {scenario.vessel.loa_m}m | Mass: {scenario.vessel.displacement_kg:.0f}kg"
    )
    cond_desc = (
        f"  Conditions: Wind {scenario.initial_tws_kt}kt | "
        f"Waves {scenario.initial_wave_height_m}m / {scenario.initial_wave_period_s}s"
    )
    print(vessel_desc)
    print(cond_desc)
    print("=" * 96)
    hdr = (
        f"{'Time (s)':<9} | {'Heel (deg)':<11} | {'Heading (deg)':<14} | "
        f"{'SOG (kt)':<9} | {'AWA (deg)':<10} | {'Yaw Rate (deg/s)':<17} | {'Events / State'}"
    )
    print(hdr)
    print("-" * 96)

    total_ticks = scenario.duration_ms // 10
    dt_s = 0.01

    for tick in range(total_ticks):
        t_ms = tick * 10
        env = world.step(t_ms)
        wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)

        # Steer straight (rudder=0) or counter-steer
        rudder_cmd = 0.0
        if t_ms >= 10500:
            rudder_cmd = -15.0  # Steer to counteract broach

        vessel = dynamics.step(
            dt_s=dt_s,
            env=env,
            rudder_deg=rudder_cmd,
            mainsheet_pct=100.0,
            wave_impact_force_n=wave_f,
            wave_impact_roll_moment_nm=wave_rm,
            wave_impact_yaw_moment_nm=wave_ym,
        )

        # Print telemetry every 1.0 second (every 100 ticks)
        if tick % 100 == 0:
            time_s = t_ms / 1000.0
            sog_kt = vessel.sog_m_s * 1.94384
            _aws_m_s, awa_deg = apparent_wind(
                u_m_s=vessel.sog_m_s * math.cos(math.radians(vessel.cog_deg - vessel.heading_deg)),
                v_m_s=vessel.sog_m_s * math.sin(math.radians(vessel.cog_deg - vessel.heading_deg)),
                heading_deg=vessel.heading_deg,
                tws_m_s=env.true_wind_speed_m_s,
                twa_deg=env.true_wind_angle_deg,
            )

            # Determine event notes
            notes = []
            if t_ms == 0:
                notes.append("Steady Sailing")
            if 10000 <= t_ms < 12000:
                notes.append("[WAVE IMPACT]")
            if 12000 <= t_ms < 16000:
                notes.append("[GUST STRIKE]")
            if abs(vessel.heel_deg) > 30.0:
                notes.append("[RUDDER VENTILATING]")
            if abs(vessel.yaw_rate_deg_s) > 2.0:
                notes.append("[WEATHER HELM ROUND-UP]")

            status_str = ", ".join(notes) if notes else "Nominal"

            row = (
                f"{time_s:5.1f} s   | {vessel.heel_deg:+6.1f} deg  | "
                f"{vessel.heading_deg:6.1f} deg     | {sog_kt:4.1f} kt   | "
                f"{awa_deg:+5.1f} deg  | {vessel.yaw_rate_deg_s:+6.2f} deg/s      | {status_str}"
            )
            print(row)

    print("=" * 96)
    print("  SIMULATION COMPLETE: 20.0s (2000 ticks at 100 Hz) evaluated.")
    print("=" * 96 + "\n")


if __name__ == "__main__":
    main()
