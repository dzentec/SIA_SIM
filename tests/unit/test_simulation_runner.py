"""Unit tests for SimulationRunner and Scenario Catalog (GOLD-01, GOLD-02)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from sia_sim.contracts.data import SensorFrame
from sia_sim.contracts.evaluation import DecisionPayload, RiskAssessment
from sia_sim.contracts.scenario import Scenario
from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios import get_benign_scenario, get_sim005_scenario, load_scenario
from sia_sim.sia.protocol import SIACore


class MinimalNullSIA(SIACore):
    """Test stub implementing SIACore that takes no action."""

    def __init__(self) -> None:
        self.frame_count = 0

    def reset(self) -> None:
        self.frame_count = 0

    def process(self, frame: SensorFrame) -> DecisionPayload:
        self.frame_count += 1
        return DecisionPayload(
            decision_id=f"DEC-{frame.sim_time_ms}",
            sim_time_ms=frame.sim_time_ms,
            sensor_frame_sequence=frame.sequence_number,
            risk_assessment=RiskAssessment(
                hazard_id=None,
                risk_score=0.0,
                confidence=1.0,
                evidence_ids=(),
            ),
            candidates=(),
            selected_response=None,
            conflict_resolution_note="Null SIA",
        )


class TestScenarioCatalog:
    def test_get_sim005_scenario_validity(self) -> None:
        scenario = get_sim005_scenario(seed=42)
        assert isinstance(scenario, Scenario)
        assert scenario.scenario_id == "SIM-005"
        assert scenario.duration_ms == 20000
        assert len(scenario.events) == 2

    def test_get_benign_scenario_validity(self) -> None:
        scenario = get_benign_scenario(seed=100)
        assert isinstance(scenario, Scenario)
        assert scenario.scenario_id == "SIM-BENIGN"
        assert len(scenario.events) == 0

    def test_load_scenario_by_name(self) -> None:
        s1 = load_scenario("SIM-005")
        assert s1.scenario_id == "SIM-005"

        s2 = load_scenario("SIM-BENIGN")
        assert s2.scenario_id == "SIM-BENIGN"

    def test_load_scenario_from_json_file(self) -> None:
        scenario = get_sim005_scenario(seed=99)
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "custom_sim005.json"
            file_path.write_text(json.dumps(scenario.model_dump()), encoding="utf-8")

            loaded = load_scenario(str(file_path), seed=99)
            assert loaded.scenario_id == "SIM-005"
            assert loaded.seed == 99


class TestSimulationRunner:
    def test_sim005_default_runner_execution_pass(self) -> None:
        runner = SimulationRunner()
        scenario = get_sim005_scenario()
        result = runner.run(scenario)

        assert result.evaluation.verdict == "PASS"
        assert result.evaluation.detection_latency_ms is not None
        assert result.evaluation.detection_latency_ms <= 1500
        assert result.evaluation.false_positives == 0
        assert result.evaluation.false_negatives == 0
        assert result.oracle_result.expected_action_type == "EASE_MAIN"
        assert result.sim_speed_ratio > 1.0  # Runs faster than real-time

    def test_benign_scenario_runner_execution_pass(self) -> None:
        runner = SimulationRunner()
        scenario = get_benign_scenario()
        result = runner.run(scenario)

        assert result.evaluation.verdict == "PASS"
        assert result.evaluation.false_positives == 0
        assert result.oracle_result.hazard_onset_ms is None

    def test_custom_sia_injection(self) -> None:
        null_sia = MinimalNullSIA()
        runner = SimulationRunner(sia_core=null_sia)
        scenario = get_sim005_scenario()
        result = runner.run(scenario)

        assert null_sia.frame_count == 2000
        # Without SIA mitigation, the unmitigated broach causes False Negative
        assert result.evaluation.verdict == "FAIL"
        assert result.evaluation.false_negatives >= 1

    def test_runner_autopilot_course_keeping(self) -> None:
        """Verify baseline course-keeping autopilot holds target heading under living wind."""
        from sia_sim.scenarios.presets import get_coastal_cruise_preset

        runner = SimulationRunner()
        scenario = get_coastal_cruise_preset(seed=42, duration_ms=10000)
        result = runner.run(scenario)

        # Check that throughout the run, heading stayed close to target (65.0 deg)
        records = result.recorder.records
        target_heading = scenario.vessel.initial_heading_deg
        for r in records[50:]:  # after initial settling
            heading_diff = abs((r.gt.vessel.heading_deg - target_heading + 180.0) % 360.0 - 180.0)
            assert heading_diff < 15.0, f"Vessel drifted to {r.gt.vessel.heading_deg} deg (target {target_heading})"
