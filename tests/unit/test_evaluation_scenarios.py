"""Integration and scenario verification tests for Oracle + Evaluator pipeline.

Covers EVAL-01, EVAL-02, EVAL-03.
"""

from __future__ import annotations

from sia_sim.contracts.data import GroundTruthFrame
from sia_sim.contracts.evaluation import DecisionPayload, RiskAssessment
from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.evaluator.evaluator import EvaluatorConfig, SimulationEvaluator
from sia_sim.evaluator.oracle import SafetyOracle
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.world import WorldModel
from sia_sim.recorder.run_recorder import RunRecorder
from sia_sim.sensors.pipeline import SensorPipeline
from sia_sim.sia.mock_sia import MockSIA


def _build_sim005_scenario() -> Scenario:
    """Builds standard SIM-005 Broach Precursor scenario matching hydrodynamic parameters."""
    return Scenario(
        scenario_id="SIM-005",
        scenario_version="1.0.0",
        name="Broach Precursor Golden Scenario",
        description="IOR monohull broach precursor dynamics verification test.",
        duration_ms=20000,
        initial_tws_kt=15.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=2.0,
        initial_wave_period_s=6.0,
        vessel=VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heading_deg=65.0,
            initial_sog_kt=5.0,
            initial_heel_deg=-15.0,
        ),
        events=(
            ScenarioEvent(
                sim_time_ms=10000,
                event_id="EVT-WAVE-01",
                event_type="wave_impact",
                parameters={
                    "impact_force_n": 12000.0,
                    "impact_roll_moment_nm": -25000.0,
                    "duration_ms": 2000,
                },
            ),
            ScenarioEvent(
                sim_time_ms=12000,
                event_id="EVT-GUST-01",
                event_type="wind_gust",
                parameters={"tws_kt": 18.0, "duration_s": 4.0, "direction_shift_deg": 15.0},
            ),
        ),
        seed=42,
    )


class TestEvaluationScenarios:
    def test_sim005_end_to_end_evaluation_pass(self) -> None:
        """Scenario 1: Runs 20s SIM-005 simulation and asserts Oracle + Evaluator PASS verdict."""
        scenario = _build_sim005_scenario()

        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)

        dynamics = VesselDynamics.from_config(scenario.vessel)
        sensor_pipeline = SensorPipeline(master_seed=scenario.seed)
        sia = MockSIA()
        recorder = RunRecorder()

        total_ticks = scenario.duration_ms // 10
        dt_s = 0.01

        active_rudder_cmd = 0.0
        active_sail_cmd = 100.0

        for tick in range(total_ticks):
            t_ms = tick * 10

            # 1. World physics step
            env = world.step(t_ms)
            wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)

            # 2. Vessel dynamics step
            vessel = dynamics.step(
                dt_s=dt_s,
                env=env,
                rudder_deg=active_rudder_cmd,
                mainsheet_pct=active_sail_cmd,
                wave_impact_force_n=wave_f,
                wave_impact_roll_moment_nm=wave_rm,
                wave_impact_yaw_moment_nm=wave_ym,
            )

            active_events = tuple(world.get_active_event_ids(t_ms))
            gt = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                active_event_ids=active_events,
                sequence_number=tick,
            )
            sf = sensor_pipeline.process(gt, ())

            # 3. SIA Core evaluation
            decision = sia.process(sf)

            # 4. Apply corrective action if recommended by SIA (simulating skipper execution)
            if decision.selected_response is not None:
                if decision.selected_response.rudder_command_deg is not None:
                    active_rudder_cmd = decision.selected_response.rudder_command_deg
                if decision.selected_response.sail_command_pct is not None:
                    active_sail_cmd = decision.selected_response.sail_command_pct
            else:
                active_rudder_cmd = 0.0
                active_sail_cmd = 100.0

            # 5. Record
            recorder.record(gt, sf, decision)

        # 6. Run Oracle Evaluation
        oracle = SafetyOracle()
        gt_frames = [r.gt for r in recorder.records]
        decisions = [r.decision for r in recorder.records]

        oracle_result = oracle.evaluate(gt_frames, scenario_id=scenario.scenario_id)

        assert oracle_result.hazard_onset_ms is not None
        assert 10000 <= oracle_result.hazard_onset_ms <= 13000
        assert oracle_result.expected_action_type == "EASE_MAIN"
        assert oracle_result.safety_envelope_breached is False

        # 7. Run Simulation Evaluator
        evaluator = SimulationEvaluator(EvaluatorConfig(max_acceptable_latency_ms=1500, require_recovery=False))
        eval_result = evaluator.evaluate(oracle_result, decisions, run_id="SIM005-RUN-01")

        assert eval_result.verdict == "PASS"
        assert eval_result.detection_latency_ms is not None
        assert eval_result.detection_latency_ms <= 1500
        assert eval_result.false_positives == 0
        assert eval_result.false_negatives == 0
        assert eval_result.safety_margin_pct >= 15.0

    def test_boundary_timing_late_response_fail(self) -> None:
        """Scenario 2: Boundary timing test where decision is delayed beyond acceptable latency."""
        scenario = _build_sim005_scenario()
        oracle = SafetyOracle()

        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)
        dynamics = VesselDynamics.from_config(scenario.vessel)

        gt_frames: list[GroundTruthFrame] = []
        for tick in range(scenario.duration_ms // 10):
            t_ms = tick * 10
            env = world.step(t_ms)
            wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)
            vessel = dynamics.step(
                dt_s=0.01,
                env=env,
                rudder_deg=0.0,
                mainsheet_pct=100.0,
                wave_impact_force_n=wave_f,
                wave_impact_roll_moment_nm=wave_rm,
                wave_impact_yaw_moment_nm=wave_ym,
            )
            gt_frames.append(
                GroundTruthFrame(
                    sim_time_ms=t_ms,
                    vessel=vessel,
                    environment=env,
                    active_event_ids=(),
                    sequence_number=tick,
                )
            )

        oracle_res = oracle.evaluate(gt_frames, scenario_id=scenario.scenario_id)
        assert oracle_res.hazard_onset_ms is not None
        t_onset = oracle_res.hazard_onset_ms

        # Synthesize delayed decision trace (detection occurs 4000ms after onset,
        # exceeding 1500ms window)
        delayed_decisions: list[DecisionPayload] = []
        for tick in range(scenario.duration_ms // 10):
            t_ms = tick * 10
            if t_ms >= t_onset + 4000:
                risk = RiskAssessment(
                    hazard_id="HAZ-BROACH-PRECURSOR",
                    risk_score=0.9,
                    confidence=1.0,
                    evidence_ids=("HIGH_HEEL",),
                )
            else:
                risk = RiskAssessment(
                    hazard_id=None,
                    risk_score=0.0,
                    confidence=1.0,
                    evidence_ids=(),
                )

            delayed_decisions.append(
                DecisionPayload(
                    decision_id=f"DEC-{t_ms}",
                    sim_time_ms=t_ms,
                    sensor_frame_sequence=tick,
                    risk_assessment=risk,
                    candidates=(),
                    selected_response=None,
                    conflict_resolution_note="Late response",
                )
            )

        evaluator = SimulationEvaluator(EvaluatorConfig(max_acceptable_latency_ms=1500, require_recovery=False))
        eval_res = evaluator.evaluate(oracle_res, delayed_decisions, run_id="LATE-RUN-01")

        assert eval_res.verdict == "FAIL"
        assert eval_res.false_negatives == 1
        assert "latency" in eval_res.notes.lower() or "window" in eval_res.notes.lower()

    def test_noisy_degraded_telemetry_evaluation(self) -> None:
        """Scenario 3: Oracle accurately evaluates ground truth despite degraded sensors."""
        scenario = _build_sim005_scenario()
        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)
        dynamics = VesselDynamics.from_config(scenario.vessel)

        # Degraded sensor pipeline with fault injection
        sensor_pipeline = SensorPipeline(master_seed=999)
        sia = MockSIA()

        gt_frames: list[GroundTruthFrame] = []
        decisions: list[DecisionPayload] = []

        for tick in range(scenario.duration_ms // 10):
            t_ms = tick * 10
            env = world.step(t_ms)
            wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)
            vessel = dynamics.step(
                dt_s=0.01,
                env=env,
                rudder_deg=0.0,
                mainsheet_pct=100.0,
                wave_impact_force_n=wave_f,
                wave_impact_roll_moment_nm=wave_rm,
                wave_impact_yaw_moment_nm=wave_ym,
            )
            gt = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                active_event_ids=(),
                sequence_number=tick,
            )
            gt_frames.append(gt)

            # Fault event: GPS and Wind drop out around T=10s..14s
            fault_event = ScenarioEvent(
                sim_time_ms=10000,
                event_id="FAULT-GPS-01",
                event_type="sensor_fault",
                parameters={"sensor": "gps", "fault_type": "loss_of_lock", "duration_ms": 4000},
            )
            active_events = (fault_event,) if 10000 <= t_ms < 14000 else ()

            sf = sensor_pipeline.process(gt, active_events)
            decision = sia.process(sf)
            decisions.append(decision)

        # Oracle operates on ground truth, unaffected by sensor faults (INV-03)
        oracle = SafetyOracle()
        oracle_res = oracle.evaluate(gt_frames, scenario_id=scenario.scenario_id)
        assert oracle_res.hazard_onset_ms is not None
        assert 10000 <= oracle_res.hazard_onset_ms <= 15000

        # SIA degraded confidence was recorded during GPS fault
        fault_decisions = [d for d in decisions if 10000 <= d.sim_time_ms < 14000]
        assert any(d.risk_assessment.confidence < 1.0 for d in fault_decisions)

    def test_benign_sailing_zero_false_positives(self) -> None:
        """Scenario 4: Benign swell condition asserts zero false alarms and PASS."""
        scenario = Scenario(
            scenario_id="SIM-BENIGN",
            scenario_version="1.0.0",
            name="Calm Reach",
            description="Benign flat calm sailing conditions with zero broach precursor risk.",
            duration_ms=10000,
            initial_tws_kt=8.0,
            initial_twa_deg=0.0,
            initial_wave_height_m=0.5,
            initial_wave_period_s=4.0,
            vessel=VesselConfig(
                vessel_type="monohull_ior",
                loa_m=10.5,
                beam_m=3.2,
                displacement_kg=4500.0,
                initial_heading_deg=45.0,
                initial_sog_kt=4.0,
                initial_heel_deg=-5.0,
            ),
            events=(),
            seed=100,
        )

        world = WorldModel.from_scenario(scenario)
        dynamics = VesselDynamics.from_config(scenario.vessel)
        sensor_pipeline = SensorPipeline(master_seed=scenario.seed)
        sia = MockSIA()
        recorder = RunRecorder()

        for tick in range(scenario.duration_ms // 10):
            t_ms = tick * 10
            env = world.step(t_ms)
            vessel = dynamics.step(dt_s=0.01, env=env, rudder_deg=0.0, mainsheet_pct=100.0)
            gt = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                active_event_ids=(),
                sequence_number=tick,
            )
            sf = sensor_pipeline.process(gt, ())
            decision = sia.process(sf)
            recorder.record(gt, sf, decision)

        oracle = SafetyOracle()
        gt_frames = [r.gt for r in recorder.records]
        decisions = [r.decision for r in recorder.records]

        oracle_res = oracle.evaluate(gt_frames, scenario_id=scenario.scenario_id)
        assert oracle_res.hazard_onset_ms is None
        assert oracle_res.severity in ("NONE", "LOW")

        evaluator = SimulationEvaluator()
        eval_res = evaluator.evaluate(oracle_res, decisions, run_id="BENIGN-01")

        assert eval_res.verdict == "PASS"
        assert eval_res.false_positives == 0
        assert eval_res.false_negatives == 0
