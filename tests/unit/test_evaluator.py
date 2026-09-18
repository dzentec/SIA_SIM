"""Unit tests for SimulationEvaluator (INV-08, EVAL-02, EVAL-03)."""

from __future__ import annotations

from sia_sim.contracts.evaluation import (
    CandidateResponse,
    DecisionPayload,
    OracleResult,
    RiskAssessment,
)
from sia_sim.evaluator.evaluator import EvaluatorConfig, SimulationEvaluator


def _make_decision(
    time_ms: int,
    seq: int = 0,
    risk_score: float = 0.0,
    hazard_id: str | None = None,
    with_candidate: bool = False,
) -> DecisionPayload:
    """Helper to build synthetic DecisionPayload."""
    candidates: tuple[CandidateResponse, ...] = ()
    selected = None
    if with_candidate:
        resp = CandidateResponse(
            response_id="R-01",
            action_type="EASE_MAIN",
            rudder_command_deg=-15.0,
            sail_command_pct=50.0,
            priority_score=0.9,
            rule_ids=("RULE-BROACH",),
        )
        candidates = (resp,)
        selected = resp

    return DecisionPayload(
        decision_id=f"DEC-{time_ms}",
        sim_time_ms=time_ms,
        sensor_frame_sequence=seq,
        risk_assessment=RiskAssessment(
            hazard_id=hazard_id,
            risk_score=risk_score,
            confidence=0.95,
            evidence_ids=("imu", "wind") if hazard_id else (),
        ),
        candidates=candidates,
        selected_response=selected,
        conflict_resolution_note="Deterministic test decision",
    )


class TestSimulationEvaluator:
    def test_pass_nominal_scenario(self) -> None:
        evaluator = SimulationEvaluator()
        oracle_result = OracleResult(
            scenario_id="SIM-NOMINAL",
            hazard_onset_ms=None,
            required_response_window_ms=None,
            expected_action_type=None,
            recovery_achieved=True,
            safety_envelope_breached=False,
            severity="NONE",
        )
        decisions = [_make_decision(t, seq=i, risk_score=0.1) for i, t in enumerate(range(0, 5000, 10))]

        result = evaluator.evaluate(oracle_result, decisions, run_id="RUN-NOMINAL-01")

        assert result.verdict == "PASS"
        assert result.false_positives == 0
        assert result.false_negatives == 0
        assert result.detection_latency_ms is None
        assert result.safety_margin_pct == 100.0

    def test_pass_timely_hazard_detection(self) -> None:
        evaluator = SimulationEvaluator(EvaluatorConfig(max_acceptable_latency_ms=1500))
        oracle_result = OracleResult(
            scenario_id="SIM-005",
            hazard_onset_ms=10000,
            required_response_window_ms=3000,
            expected_action_type="EASE_MAIN",
            recovery_achieved=True,
            safety_envelope_breached=False,
            severity="CRITICAL",
        )
        decisions = []
        # T=0..10.0s: nominal
        for i, t in enumerate(range(0, 10000, 10)):
            decisions.append(_make_decision(t, seq=i, risk_score=0.1))
        # T=10.0s..10.5s: nominal transition
        for i, t in enumerate(range(10000, 10500, 10), start=len(decisions)):
            decisions.append(_make_decision(t, seq=i, risk_score=0.2))
        # T=10.5s (latency = 500 ms): SIA detects broach
        for i, t in enumerate(range(10500, 20000, 10), start=len(decisions)):
            decisions.append(
                _make_decision(
                    t,
                    seq=i,
                    risk_score=0.85,
                    hazard_id="BROACH_PRECURSOR",
                    with_candidate=True,
                )
            )

        result = evaluator.evaluate(oracle_result, decisions, run_id="RUN-BROACH-PASS")

        assert result.verdict == "PASS"
        assert result.detection_latency_ms == 500
        assert result.false_positives == 0
        assert result.false_negatives == 0
        assert result.safety_margin_pct > 80.0

    def test_fail_excessive_latency(self) -> None:
        evaluator = SimulationEvaluator(EvaluatorConfig(max_acceptable_latency_ms=1000))
        oracle_result = OracleResult(
            scenario_id="SIM-005",
            hazard_onset_ms=10000,
            required_response_window_ms=1000,
            expected_action_type="EASE_MAIN",
            recovery_achieved=True,
            safety_envelope_breached=False,
            severity="CRITICAL",
        )
        # SIA only detects at T=11500 (latency = 1500 ms > 1000 ms limit)
        decisions = []
        for i, t in enumerate(range(0, 11500, 10)):
            decisions.append(_make_decision(t, seq=i, risk_score=0.1))
        for i, t in enumerate(range(11500, 20000, 10), start=len(decisions)):
            decisions.append(
                _make_decision(
                    t,
                    seq=i,
                    risk_score=0.9,
                    hazard_id="BROACH_PRECURSOR",
                    with_candidate=True,
                )
            )

        result = evaluator.evaluate(oracle_result, decisions, run_id="RUN-SLOW-FAIL")

        assert result.verdict == "FAIL"
        assert result.detection_latency_ms == 1500
        assert result.false_negatives == 1
        assert "exceeded" in result.notes

    def test_fail_false_negatives_no_detection(self) -> None:
        evaluator = SimulationEvaluator()
        oracle_result = OracleResult(
            scenario_id="SIM-005",
            hazard_onset_ms=10000,
            required_response_window_ms=3000,
            expected_action_type="EASE_MAIN",
            recovery_achieved=False,
            safety_envelope_breached=False,
            severity="CRITICAL",
        )
        # SIA never detects anything
        decisions = [_make_decision(t, seq=i, risk_score=0.1) for i, t in enumerate(range(0, 20000, 10))]

        result = evaluator.evaluate(oracle_result, decisions, run_id="RUN-MISSED-FAIL")

        assert result.verdict == "FAIL"
        assert result.false_negatives == 1
        assert result.detection_latency_ms is None

    def test_fail_false_positives_in_calm(self) -> None:
        evaluator = SimulationEvaluator(EvaluatorConfig(max_allowed_false_positives=0))
        oracle_result = OracleResult(
            scenario_id="SIM-NOMINAL",
            hazard_onset_ms=None,
            required_response_window_ms=None,
            expected_action_type=None,
            recovery_achieved=True,
            safety_envelope_breached=False,
            severity="NONE",
        )
        # SIA triggers false alarm at t=2000
        decisions = []
        for i, t in enumerate(range(0, 5000, 10)):
            risk = 0.9 if t == 2000 else 0.05
            hazard = "FALSE_ALARM" if t == 2000 else None
            decisions.append(_make_decision(t, seq=i, risk_score=risk, hazard_id=hazard))

        result = evaluator.evaluate(oracle_result, decisions, run_id="RUN-FP-FAIL")

        assert result.verdict == "FAIL"
        assert result.false_positives == 1

    def test_fail_safety_envelope_breach(self) -> None:
        evaluator = SimulationEvaluator()
        oracle_result = OracleResult(
            scenario_id="SIM-005",
            hazard_onset_ms=10000,
            required_response_window_ms=3000,
            expected_action_type="EASE_MAIN",
            recovery_achieved=False,
            safety_envelope_breached=True,
            severity="CRITICAL",
        )
        decisions = [
            _make_decision(t, seq=i, risk_score=0.8, hazard_id="BROACH_PRECURSOR", with_candidate=True)
            for i, t in enumerate(range(0, 15000, 10))
        ]

        result = evaluator.evaluate(oracle_result, decisions, run_id="RUN-BREACH-FAIL")

        assert result.verdict == "FAIL"
        assert result.safety_margin_pct < 0
