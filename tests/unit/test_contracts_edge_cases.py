"""Edge cases, rejection tests, immutability, and None-preservation for contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sia_sim.contracts.data import (
    ActuatorState,
    GPSReading,
    GroundTruthFrame,
    IMUReading,
    SensorFrame,
    WindReading,
)
from sia_sim.contracts.evaluation import (
    CandidateResponse,
    DecisionPayload,
    EvaluationResult,
    OracleResult,
    RiskAssessment,
)
from sia_sim.contracts.scenario import Scenario, VesselConfig

# ---------------------------------------------------------------------------
# Task 1: Edge-case rejection tests
# ---------------------------------------------------------------------------


class TestSensorFrameEdgeCases:
    def test_sim_time_ms_must_be_int(
        self,
        minimal_imu_all_failed: IMUReading,
        minimal_gps_no_fix: GPSReading,
        minimal_wind_failed: WindReading,
        minimal_actuators_no_feedback: ActuatorState,
    ) -> None:
        with pytest.raises(ValidationError):
            SensorFrame(
                sim_time_ms=10.5,  # type: ignore[arg-type]
                imu=minimal_imu_all_failed,
                gps=minimal_gps_no_fix,
                wind=minimal_wind_failed,
                actuators=minimal_actuators_no_feedback,
                sequence_number=0,
            )

    def test_sequence_number_cannot_be_negative(
        self,
        minimal_imu_all_failed: IMUReading,
        minimal_gps_no_fix: GPSReading,
        minimal_wind_failed: WindReading,
        minimal_actuators_no_feedback: ActuatorState,
    ) -> None:
        with pytest.raises(ValidationError):
            invalid_seq = int("-1")
            SensorFrame(
                sim_time_ms=0,
                imu=minimal_imu_all_failed,
                gps=minimal_gps_no_fix,
                wind=minimal_wind_failed,
                actuators=minimal_actuators_no_feedback,
                sequence_number=invalid_seq,
            )

    def test_imu_missing_raises(
        self,
        minimal_gps_no_fix: GPSReading,
        minimal_wind_failed: WindReading,
        minimal_actuators_no_feedback: ActuatorState,
    ) -> None:
        with pytest.raises(ValidationError):
            SensorFrame(
                sim_time_ms=0,
                imu=None,  # type: ignore[arg-type]
                gps=minimal_gps_no_fix,
                wind=minimal_wind_failed,
                actuators=minimal_actuators_no_feedback,
                sequence_number=0,
            )

    def test_imu_fault_true_all_none_valid(self, minimal_imu_all_failed: IMUReading) -> None:
        assert minimal_imu_all_failed.fault is True
        assert minimal_imu_all_failed.roll_deg is None

    def test_imu_fault_false_partial_none_valid(self) -> None:
        imu = IMUReading(
            roll_deg=10.0,
            pitch_deg=None,
            roll_rate_deg_s=None,
            pitch_rate_deg_s=None,
            yaw_rate_deg_s=None,
            accel_x_m_s2=None,
            accel_y_m_s2=None,
            accel_z_m_s2=None,
            fault=False,
        )
        assert imu.roll_deg == 10.0
        assert imu.pitch_deg is None


class TestGroundTruthFrameEdgeCases:
    def test_sim_time_must_be_int(self, minimal_ground_truth_frame: GroundTruthFrame) -> None:
        with pytest.raises(ValidationError):
            GroundTruthFrame(
                sim_time_ms=10.5,  # type: ignore[arg-type]
                vessel=minimal_ground_truth_frame.vessel,
                environment=minimal_ground_truth_frame.environment,
                sequence_number=0,
                active_event_ids=(),
            )

    def test_active_event_ids_empty_tuple_valid(self, minimal_ground_truth_frame: GroundTruthFrame) -> None:
        assert minimal_ground_truth_frame.active_event_ids == ()

    def test_active_event_ids_must_be_tuple_not_list(self, minimal_ground_truth_frame: GroundTruthFrame) -> None:
        with pytest.raises(ValidationError):
            GroundTruthFrame(
                sim_time_ms=0,
                vessel=minimal_ground_truth_frame.vessel,
                environment=minimal_ground_truth_frame.environment,
                sequence_number=0,
                active_event_ids=["EVT-001"],  # type: ignore[arg-type]
            )


class TestScenarioEdgeCases:
    def test_empty_events_schedule_valid(self, minimal_scenario: Scenario) -> None:
        data = minimal_scenario.model_dump()
        data["events"] = ()
        scenario = Scenario.model_validate(data)
        assert scenario.events == ()

    def test_duration_must_be_positive_int(self, minimal_scenario: Scenario) -> None:
        data = minimal_scenario.model_dump()
        data["duration_ms"] = 0
        with pytest.raises(ValidationError):
            Scenario.model_validate(data)

    def test_seed_can_be_zero_or_negative(self, minimal_scenario: Scenario) -> None:
        d0 = minimal_scenario.model_dump()
        d0["seed"] = 0
        s0 = Scenario.model_validate(d0)
        assert s0.seed == 0

        d_neg = minimal_scenario.model_dump()
        d_neg["seed"] = -42
        s_neg = Scenario.model_validate(d_neg)
        assert s_neg.seed == -42

    def test_vessel_displacement_must_be_numeric(self) -> None:
        with pytest.raises(ValidationError):
            VesselConfig(
                vessel_type="monohull",
                loa_m=10.0,
                beam_m=3.0,
                displacement_kg="heavy",  # type: ignore[arg-type]
                initial_heel_deg=0.0,
                initial_heading_deg=0.0,
                initial_sog_kt=5.0,
            )


class TestDecisionPayloadEdgeCases:
    def test_candidates_cannot_exceed_three(self, minimal_decision_payload: DecisionPayload) -> None:
        cand = CandidateResponse(
            response_id="R",
            action_type="ACT",
            rudder_command_deg=None,
            sail_command_pct=None,
            priority_score=1.0,
            rule_ids=(),
        )
        data = minimal_decision_payload.model_dump()
        data["candidates"] = (cand.model_dump(),) * 4
        with pytest.raises(ValidationError):
            DecisionPayload.model_validate(data)

    def test_empty_candidates_with_none_selected_valid(self, minimal_decision_payload: DecisionPayload) -> None:
        assert minimal_decision_payload.candidates == ()
        assert minimal_decision_payload.selected_response is None

    def test_risk_score_bounds_rejection(self) -> None:
        with pytest.raises(ValidationError):
            RiskAssessment(
                hazard_id=None,
                risk_score=1.01,
                confidence=0.5,
                evidence_ids=(),
            )
        with pytest.raises(ValidationError):
            RiskAssessment(
                hazard_id=None,
                risk_score=-0.01,
                confidence=0.5,
                evidence_ids=(),
            )

    def test_confidence_bounds_rejection(self) -> None:
        with pytest.raises(ValidationError):
            RiskAssessment(
                hazard_id=None,
                risk_score=0.5,
                confidence=1.1,
                evidence_ids=(),
            )


class TestEvaluationResultEdgeCases:
    def test_verdict_invalid_string_rejected(self, minimal_evaluation_result_pass: EvaluationResult) -> None:
        data = minimal_evaluation_result_pass.model_dump()
        data["verdict"] = "UNKNOWN"
        with pytest.raises(ValidationError):
            EvaluationResult.model_validate(data)

    def test_false_positives_negatives_non_negative(self, minimal_evaluation_result_pass: EvaluationResult) -> None:
        d1 = minimal_evaluation_result_pass.model_dump()
        d1["false_positives"] = -1
        with pytest.raises(ValidationError):
            EvaluationResult.model_validate(d1)

        d2 = minimal_evaluation_result_pass.model_dump()
        d2["false_negatives"] = -1
        with pytest.raises(ValidationError):
            EvaluationResult.model_validate(d2)

    def test_detection_latency_none_valid(self, minimal_evaluation_result_pass: EvaluationResult) -> None:
        data = minimal_evaluation_result_pass.model_dump()
        data["detection_latency_ms"] = None
        res = EvaluationResult.model_validate(data)
        assert res.detection_latency_ms is None

    def test_safety_margin_negative_allowed(self, minimal_evaluation_result_pass: EvaluationResult) -> None:
        data = minimal_evaluation_result_pass.model_dump()
        data["safety_margin_pct"] = -15.5
        res = EvaluationResult.model_validate(data)
        assert res.safety_margin_pct == -15.5


# ---------------------------------------------------------------------------
# Task 2: Immutability verification tests
# ---------------------------------------------------------------------------


class TestImmutabilityAcrossContracts:
    def test_sensor_frame_is_frozen(self, minimal_sensor_frame: SensorFrame) -> None:
        with pytest.raises(ValidationError):
            setattr(minimal_sensor_frame, "sequence_number", 999)  # noqa: B010

    def test_ground_truth_frame_is_frozen(self, minimal_ground_truth_frame: GroundTruthFrame) -> None:
        with pytest.raises(ValidationError):
            setattr(minimal_ground_truth_frame, "sim_time_ms", 999)  # noqa: B010

    def test_scenario_is_frozen(self, minimal_scenario: Scenario) -> None:
        with pytest.raises(ValidationError):
            setattr(minimal_scenario, "seed", 999)  # noqa: B010

    def test_decision_payload_is_frozen(self, minimal_decision_payload: DecisionPayload) -> None:
        with pytest.raises(ValidationError):
            setattr(minimal_decision_payload, "decision_id", "hacked")  # noqa: B010

    def test_oracle_result_is_frozen(self, minimal_oracle_result_no_hazard: OracleResult) -> None:
        with pytest.raises(ValidationError):
            setattr(minimal_oracle_result_no_hazard, "recovery_achieved", False)  # noqa: B010

    def test_evaluation_result_is_frozen(self, minimal_evaluation_result_pass: EvaluationResult) -> None:
        with pytest.raises(ValidationError):
            setattr(minimal_evaluation_result_pass, "verdict", "FAIL")  # noqa: B010


# ---------------------------------------------------------------------------
# Task 3: None preservation / no zero-coercion tests
# ---------------------------------------------------------------------------


class TestNonePreservationAcrossContracts:
    def test_none_imu_fields_preserved_in_model_dump(self, minimal_sensor_frame: SensorFrame) -> None:
        dumped = minimal_sensor_frame.model_dump()
        imu = dumped["imu"]
        assert imu["roll_deg"] is None, "None must not be coerced to 0.0"
        assert imu["roll_rate_deg_s"] is None, "None must not be coerced to 0.0"
        assert "roll_deg" in imu, "None field must not be omitted from dump"

    def test_none_gps_fields_preserved_in_model_dump(self, minimal_sensor_frame: SensorFrame) -> None:
        dumped = minimal_sensor_frame.model_dump()
        gps = dumped["gps"]
        assert gps["latitude_deg"] is None
        assert gps["sog_kt"] is None
        assert "latitude_deg" in gps

    def test_none_oracle_timing_preserved(self, minimal_oracle_result_no_hazard: OracleResult) -> None:
        dumped = minimal_oracle_result_no_hazard.model_dump()
        assert dumped["hazard_onset_ms"] is None
        assert dumped["required_response_window_ms"] is None
        assert "hazard_onset_ms" in dumped

    def test_none_evaluation_latency_preserved(self, minimal_evaluation_result_pass: EvaluationResult) -> None:
        res = minimal_evaluation_result_pass.model_copy(update={"detection_latency_ms": None})
        dumped = res.model_dump()
        assert dumped["detection_latency_ms"] is None
        assert "detection_latency_ms" in dumped
