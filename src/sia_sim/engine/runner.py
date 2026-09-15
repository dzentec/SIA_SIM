"""Central SimulationRunner orchestrating the deterministic 100 Hz simulation loop (GOLD-02)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sia_sim.contracts.data import GroundTruthFrame
from sia_sim.evaluator.evaluator import EvaluatorConfig, SimulationEvaluator
from sia_sim.evaluator.oracle import OracleConfig, SafetyOracle
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.world import WorldModel
from sia_sim.recorder.run_recorder import RunRecorder
from sia_sim.sensors.pipeline import SensorPipeline
from sia_sim.sia.mock_sia import MockSIA

if TYPE_CHECKING:
    from sia_sim.contracts.evaluation import EvaluationResult, OracleResult
    from sia_sim.contracts.scenario import Scenario
    from sia_sim.sia.protocol import SIACore


@dataclass(frozen=True)
class SimulationRunResult:
    """Structured result of an end-to-end simulation execution."""

    scenario: Scenario
    evaluation: EvaluationResult
    oracle_result: OracleResult
    recorder: RunRecorder
    elapsed_wall_time_s: float
    sim_speed_ratio: float


class SimulationRunner:
    """Synchronous, deterministic 100 Hz simulation testbed orchestrator.

    Integrates WorldModel, VesselDynamics, SensorPipeline, SIACore, RunRecorder,
    SafetyOracle, and SimulationEvaluator without wall-clock dependencies.
    """

    def __init__(
        self,
        sia_core: SIACore | None = None,
        oracle_config: OracleConfig | None = None,
        evaluator_config: EvaluatorConfig | None = None,
        imu_sample_rate_hz: int = 100,
        imu_lpf_cutoff_hz: float = 20.0,
    ) -> None:
        self.sia_core: SIACore = sia_core or MockSIA()
        self.oracle_config = oracle_config or OracleConfig()
        self.evaluator_config = evaluator_config or EvaluatorConfig()
        self.imu_sample_rate_hz = imu_sample_rate_hz
        self.imu_lpf_cutoff_hz = imu_lpf_cutoff_hz

    def run(
        self,
        scenario: Scenario,
        run_id: str | None = None,
        apply_actuator_feedback: bool = True,
        imu_sample_rate_hz: int | None = None,
        imu_lpf_cutoff_hz: float | None = None,
    ) -> SimulationRunResult:
        """Executes a full scenario from start to finish and computes objective evaluation."""
        run_id = run_id or f"RUN-{scenario.scenario_id}-{scenario.seed}"

        # 1. Initialize simulation subsystems
        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)

        effective_rate = imu_sample_rate_hz or self.imu_sample_rate_hz
        effective_lpf = imu_lpf_cutoff_hz or self.imu_lpf_cutoff_hz

        dynamics = VesselDynamics.from_config(scenario.vessel)
        sensor_pipeline = SensorPipeline(
            master_seed=scenario.seed,
            imu_sample_rate_hz=effective_rate,
            imu_lpf_cutoff_hz=effective_lpf,
        )
        self.sia_core.reset()
        recorder = RunRecorder()

        total_ticks = scenario.duration_ms // 10
        dt_s = 0.01

        active_rudder_cmd = 0.0
        active_sail_cmd = 100.0

        start_time = time.perf_counter()

        # 2. Synchronous fixed-step 100 Hz loop
        for tick in range(total_ticks):
            t_ms = tick * 10

            # Step 1: Advance environmental ground truth physics
            env = world.step(t_ms)
            wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)
            heading_now_deg = math.degrees(dynamics._state[2])
            _elev, amb_rm, _amb_pm, _vert_a = world.wave.evaluate_ambient_excitation(
                x_m=float(dynamics._state[0]),
                y_m=float(dynamics._state[1]),
                time_s=t_ms / 1000.0,
                heading_deg=heading_now_deg,
                mass_kg=dynamics.mass,
            )

            # Step 2: Step vessel 3-DoF planar dynamics with continuous wave excitation
            vessel = dynamics.step(
                dt_s=dt_s,
                env=env,
                rudder_deg=active_rudder_cmd,
                mainsheet_pct=active_sail_cmd,
                wave_impact_force_n=wave_f,
                wave_impact_roll_moment_nm=wave_rm,
                wave_impact_yaw_moment_nm=wave_ym,
                ambient_wave_roll_moment_nm=amb_rm,
            )

            active_event_objs = tuple(world.get_active_events(t_ms))
            active_events = tuple(evt.event_id for evt in active_event_objs)
            gt = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                active_event_ids=active_events,
                sequence_number=tick,
            )

            # Step 3: Degrade ground truth into observable SensorFrame (INV-01, INV-02)
            sf = sensor_pipeline.process(gt, active_event_objs)

            # Step 4: Feed SensorFrame to SIA Core
            decision = self.sia_core.process(sf)

            # Step 5: Closed-loop actuator feedback (if enabled)
            if apply_actuator_feedback and decision.selected_response is not None:
                if decision.selected_response.rudder_command_deg is not None:
                    active_rudder_cmd = decision.selected_response.rudder_command_deg
                if decision.selected_response.sail_command_pct is not None:
                    active_sail_cmd = decision.selected_response.sail_command_pct
            else:
                active_rudder_cmd = 0.0
                active_sail_cmd = 100.0

            # Step 6: Log telemetry and decision
            recorder.record(gt, sf, decision)

        elapsed_wall_time = time.perf_counter() - start_time
        sim_duration_s = scenario.duration_ms / 1000.0
        sim_speed_ratio = sim_duration_s / max(0.0001, elapsed_wall_time)

        # 3. Post-run independent Oracle Evaluation (INV-03)
        oracle = SafetyOracle(self.oracle_config)
        gt_frames = [r.gt for r in recorder.records]
        decisions = [r.decision for r in recorder.records]
        oracle_result = oracle.evaluate(gt_frames, scenario_id=scenario.scenario_id)

        # 4. Objective Simulation Evaluator scoring (INV-08)
        evaluator = SimulationEvaluator(self.evaluator_config)
        evaluation = evaluator.evaluate(oracle_result, decisions, run_id=run_id)

        return SimulationRunResult(
            scenario=scenario,
            evaluation=evaluation,
            oracle_result=oracle_result,
            recorder=recorder,
            elapsed_wall_time_s=elapsed_wall_time,
            sim_speed_ratio=round(sim_speed_ratio, 2),
        )
