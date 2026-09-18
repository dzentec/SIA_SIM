"""Unit tests for DecisionPayload, OracleResult, and EvaluationResult data contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sia_sim.contracts.evaluation import (
    CandidateResponse,
    DecisionPayload,
    EvaluationResult,
    OracleResult,
    RiskAssessment,
)


@pytest.fixture
def sample_risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        hazard_id="HAZ-BROACH-01",
        risk_score=0.85,
        confidence=0.92,
        evidence_ids=("imu.roll_deg", "imu.yaw_rate_deg_s", "actuators.rudder_angle_deg"),
    )


@pytest.fixture
def sample_candidate_1() -> CandidateResponse:
    return CandidateResponse(
        response_id="RESP-001",
        action_type="REDUCE_SAIL",
        rudder_command_deg=None,
        sail_command_pct=50.0,
        priority_score=0.9,
        rule_ids=("RULE-BROACH-PREVENT-01",),
    )


@pytest.fixture
def sample_candidate_2() -> CandidateResponse:
    return CandidateResponse(
        response_id="RESP-002",
        action_type="ALTER_COURSE",
        rudder_command_deg=-15.0,
        sail_command_pct=None,
        priority_score=0.75,
        rule_ids=("RULE-RUDDER-CORRECT-02",),
    )


@pytest.fixture
def sample_candidate_3() -> CandidateResponse:
    return CandidateResponse(
        response_id="RESP-003",
        action_type="ALERT_CREW",
        rudder_command_deg=None,
        sail_command_pct=None,
        priority_score=0.6,
        rule_ids=("RULE-EARLY-WARNING-01",),
    )


@pytest.fixture
def sample_decision_payload(
    sample_risk_assessment: RiskAssessment,
    sample_candidate_1: CandidateResponse,
    sample_candidate_2: CandidateResponse,
) -> DecisionPayload:
    return DecisionPayload(
        decision_id="DEC-000100",
        sim_time_ms=15000,
        sensor_frame_sequence=1500,
        risk_assessment=sample_risk_assessment,
        candidates=(sample_candidate_1, sample_candidate_2),
        selected_response=sample_candidate_1,
        conflict_resolution_note="Selected candidate 1 due to higher priority score.",
    )


@pytest.fixture
def sample_oracle_result() -> OracleResult:
    return OracleResult(
        scenario_id="SIM-005",
        hazard_onset_ms=15000,
        required_response_window_ms=2000,
        expected_action_type="REDUCE_SAIL",
        recovery_achieved=True,
        safety_envelope_breached=False,
        severity="HIGH",
    )


@pytest.fixture
def sample_evaluation_result() -> EvaluationResult:
    return EvaluationResult(
        scenario_id="SIM-005",
        run_id="RUN-20260915-001",
        verdict="PASS",
        detection_latency_ms=450,
        false_positives=0,
        false_negatives=0,
        safety_margin_pct=77.5,
        notes="SIA Core successfully prevented broach with 77.5% safety margin remaining.",
    )


class TestDecisionPayload:
    def test_zero_candidates_valid(self, sample_risk_assessment: RiskAssessment) -> None:
        payload = DecisionPayload(
            decision_id="DEC-000001",
            sim_time_ms=0,
            sensor_frame_sequence=0,
            risk_assessment=sample_risk_assessment,
            candidates=(),
            selected_response=None,
            conflict_resolution_note="No action needed.",
        )
        assert len(payload.candidates) == 0
        assert payload.selected_response is None

    def test_three_candidates_valid(
        self,
        sample_risk_assessment: RiskAssessment,
        sample_candidate_1: CandidateResponse,
        sample_candidate_2: CandidateResponse,
        sample_candidate_3: CandidateResponse,
    ) -> None:
        payload = DecisionPayload(
            decision_id="DEC-000002",
            sim_time_ms=15000,
            sensor_frame_sequence=1500,
            risk_assessment=sample_risk_assessment,
            candidates=(sample_candidate_1, sample_candidate_2, sample_candidate_3),
            selected_response=sample_candidate_1,
            conflict_resolution_note="Selected response with highest priority.",
        )
        assert len(payload.candidates) == 3

    def test_more_than_three_candidates_raises(
        self,
        sample_risk_assessment: RiskAssessment,
        sample_candidate_1: CandidateResponse,
        sample_candidate_2: CandidateResponse,
        sample_candidate_3: CandidateResponse,
    ) -> None:
        cand4 = CandidateResponse(
            response_id="RESP-004",
            action_type="STAND_BY",
            rudder_command_deg=None,
            sail_command_pct=None,
            priority_score=0.1,
            rule_ids=(),
        )
        with pytest.raises(ValidationError):
            DecisionPayload(
                decision_id="DEC-000003",
                sim_time_ms=15000,
                sensor_frame_sequence=1500,
                risk_assessment=sample_risk_assessment,
                candidates=(
                    sample_candidate_1,
                    sample_candidate_2,
                    sample_candidate_3,
                    cand4,
                ),
                selected_response=sample_candidate_1,
                conflict_resolution_note="Exceeded 3 candidate limit.",
            )


class TestRiskAssessmentValidation:
    def test_risk_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            RiskAssessment(
                hazard_id=None,
                risk_score=1.5,  # > 1.0
                confidence=0.5,
                evidence_ids=(),
            )

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            RiskAssessment(
                hazard_id=None,
                risk_score=0.5,
                confidence=-0.1,  # < 0.0
                evidence_ids=(),
            )


class TestOracleAndEvaluatorContracts:
    def test_oracle_result_no_hazard_valid(self) -> None:
        res = OracleResult(
            scenario_id="SIM-001",
            hazard_onset_ms=None,
            required_response_window_ms=None,
            expected_action_type=None,
            recovery_achieved=True,
            safety_envelope_breached=False,
            severity="NONE",
        )
        assert res.hazard_onset_ms is None
        assert res.severity == "NONE"

    def test_evaluation_verdict_strict_pass_fail(self) -> None:
        with pytest.raises(ValidationError):
            EvaluationResult(
                scenario_id="SIM-005",
                run_id="RUN-1",
                verdict="INCONCLUSIVE",  # type: ignore[arg-type]
                detection_latency_ms=100,
                false_positives=0,
                false_negatives=0,
                safety_margin_pct=50.0,
                notes="Invalid verdict string",
            )


class TestImmutability:
    def test_decision_payload_is_frozen(self, sample_decision_payload: DecisionPayload) -> None:
        with pytest.raises(ValidationError):
            setattr(sample_decision_payload, "decision_id", "HACKED")  # noqa: B010

    def test_oracle_result_is_frozen(self, sample_oracle_result: OracleResult) -> None:
        with pytest.raises(ValidationError):
            setattr(sample_oracle_result, "recovery_achieved", False)  # noqa: B010

    def test_evaluation_result_is_frozen(self, sample_evaluation_result: EvaluationResult) -> None:
        with pytest.raises(ValidationError):
            setattr(sample_evaluation_result, "verdict", "FAIL")  # noqa: B010


class TestRoundTrip:
    def test_decision_payload_json_round_trip(self, sample_decision_payload: DecisionPayload) -> None:
        json_str = sample_decision_payload.model_dump_json()
        restored = DecisionPayload.model_validate_json(json_str)
        assert restored == sample_decision_payload

    def test_evaluation_result_json_round_trip(self, sample_evaluation_result: EvaluationResult) -> None:
        json_str = sample_evaluation_result.model_dump_json()
        restored = EvaluationResult.model_validate_json(json_str)
        assert restored == sample_evaluation_result
