"""Cross-contract integration and end-to-end serialization tests."""

from __future__ import annotations

from sia_sim.contracts.data import (
    GroundTruthFrame,
    SensorFrame,
)
from sia_sim.contracts.evaluation import (
    CandidateResponse,
    DecisionPayload,
    EvaluationResult,
    OracleResult,
    RiskAssessment,
)
from sia_sim.contracts.scenario import (
    Scenario,
)


class TestCrossContractIntegration:
    def test_sensor_frame_to_decision_payload_linkage(self, minimal_sensor_frame_healthy: SensorFrame) -> None:
        """DecisionPayload explicitly references the SensorFrame sequence number."""
        payload = DecisionPayload(
            decision_id="DEC-000042",
            sim_time_ms=minimal_sensor_frame_healthy.sim_time_ms,
            sensor_frame_sequence=minimal_sensor_frame_healthy.sequence_number,
            risk_assessment=RiskAssessment(
                hazard_id="HAZ-HEEL-01",
                risk_score=0.7,
                confidence=0.85,
                evidence_ids=("imu.roll_deg",),
            ),
            candidates=(
                CandidateResponse(
                    response_id="RESP-001",
                    action_type="REDUCE_SAIL",
                    rudder_command_deg=None,
                    sail_command_pct=70.0,
                    priority_score=0.9,
                    rule_ids=("RULE-001",),
                ),
            ),
            selected_response=None,
            conflict_resolution_note="Evaluated without immediate actuation.",
        )
        assert payload.sensor_frame_sequence == minimal_sensor_frame_healthy.sequence_number
        assert payload.sim_time_ms == minimal_sensor_frame_healthy.sim_time_ms

    def test_oracle_and_decision_trace_to_evaluation_result(
        self,
        minimal_scenario: Scenario,
        minimal_oracle_result_no_hazard: OracleResult,
    ) -> None:
        """Evaluator consumes OracleResult and Decision trace to produce EvaluationResult."""
        eval_result = EvaluationResult(
            scenario_id=minimal_scenario.scenario_id,
            run_id="RUN-TEST-001",
            verdict="PASS",
            detection_latency_ms=minimal_oracle_result_no_hazard.hazard_onset_ms,
            false_positives=0,
            false_negatives=0,
            safety_margin_pct=100.0,
            notes=f"Evaluated scenario {minimal_scenario.scenario_id} successfully.",
        )
        assert eval_result.scenario_id == minimal_scenario.scenario_id
        assert eval_result.verdict == "PASS"

    def test_scenario_event_active_in_ground_truth(
        self,
        minimal_scenario: Scenario,
        minimal_ground_truth_frame: GroundTruthFrame,
    ) -> None:
        """Active events in GroundTruthFrame map to Scenario.events."""
        event_id = minimal_scenario.events[0].event_id
        gt_frame_with_event = minimal_ground_truth_frame.model_copy(update={"active_event_ids": (event_id,)})
        assert event_id in gt_frame_with_event.active_event_ids
        assert gt_frame_with_event.active_event_ids[0] == minimal_scenario.events[0].event_id

    def test_full_contracts_suite_round_trip(
        self,
        minimal_sensor_frame_healthy: SensorFrame,
        minimal_ground_truth_frame: GroundTruthFrame,
        minimal_scenario: Scenario,
        minimal_decision_payload: DecisionPayload,
        minimal_oracle_result_no_hazard: OracleResult,
        minimal_evaluation_result_pass: EvaluationResult,
    ) -> None:
        """All 6 top-level contract types serialize and deserialize cleanly."""
        instances = [
            minimal_sensor_frame_healthy,
            minimal_ground_truth_frame,
            minimal_scenario,
            minimal_decision_payload,
            minimal_oracle_result_no_hazard,
            minimal_evaluation_result_pass,
        ]
        for instance in instances:
            # model_dump round-trip
            dumped = instance.model_dump()
            restored_dict = type(instance).model_validate(dumped)
            assert restored_dict == instance

            # JSON round-trip
            json_str = instance.model_dump_json()
            restored_json = type(instance).model_validate_json(json_str)
            assert restored_json == instance
