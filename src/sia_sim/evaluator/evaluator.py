"""Objective Simulation Evaluator for SIA Simulation (INV-08, EVAL-02, EVAL-03).

Compares SIA DecisionPayload traces against independent OracleResult benchmarks
to compute detection latency, false positives/negatives, safety margins, and
deterministic PASS/FAIL verdicts.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sia_sim.contracts.evaluation import DecisionPayload, EvaluationResult, OracleResult


@dataclass(frozen=True)
class EvaluatorConfig:
    """Configuration parameters for simulation evaluation scoring."""

    max_acceptable_latency_ms: int = 1500
    """Maximum allowed detection latency in ms from hazard onset for a PASS verdict."""

    max_allowed_false_positives: int = 0
    """Maximum permitted false positive detections in benign conditions."""

    min_safety_margin_pct: float = 15.0
    """Minimum safety margin percentage required at response time."""

    require_recovery: bool = True
    """Whether physical recovery by scenario conclusion is mandatory for PASS."""

    risk_detection_threshold: float = 0.5
    """Minimum risk score considered an active hazard detection."""


class SimulationEvaluator:
    """Evaluates SIA Core decision streams against Oracle ground truth benchmarks."""

    def __init__(self, config: EvaluatorConfig | None = None) -> None:
        self.config = config or EvaluatorConfig()

    def evaluate(
        self,
        oracle_result: OracleResult,
        decisions: Sequence[DecisionPayload],
        run_id: str = "run-001",
    ) -> EvaluationResult:
        """Evaluates decisions against Oracle expectations and returns an EvaluationResult."""
        scenario_id = oracle_result.scenario_id
        t_onset = oracle_result.hazard_onset_ms
        window_ms = (
            oracle_result.required_response_window_ms or self.config.max_acceptable_latency_ms
        )

        false_positives = 0
        false_negatives = 0
        detection_latency_ms: int | None = None
        safety_margin_pct: float = 100.0
        failure_reasons: list[str] = []

        if t_onset is None:
            # Nominal / Benign scenario: any high-risk detection is a false positive
            for d in decisions:
                if (
                    d.risk_assessment.risk_score >= self.config.risk_detection_threshold
                    or d.risk_assessment.hazard_id is not None
                    or len(d.candidates) > 0
                ):
                    false_positives += 1

            if false_positives > self.config.max_allowed_false_positives:
                failure_reasons.append(
                    f"False positive detections ({false_positives}) exceeded "
                    f"limit ({self.config.max_allowed_false_positives})."
                )
            safety_margin_pct = 100.0

        else:
            # Active hazard scenario
            # 1. Check for false alarms before hazard onset
            for d in decisions:
                if d.sim_time_ms < t_onset - 500:
                    if (
                        d.risk_assessment.risk_score >= self.config.risk_detection_threshold
                        or d.risk_assessment.hazard_id is not None
                    ):
                        false_positives += 1

            if false_positives > self.config.max_allowed_false_positives:
                failure_reasons.append(
                    f"Premature false alarms ({false_positives}) before "
                    f"hazard onset at {t_onset}ms."
                )

            # 2. Find first valid detection on or after onset
            detection_decision = next(
                (
                    d
                    for d in decisions
                    if d.sim_time_ms >= t_onset - 200
                    and (
                        d.risk_assessment.risk_score >= self.config.risk_detection_threshold
                        or d.risk_assessment.hazard_id is not None
                        or len(d.candidates) > 0
                    )
                ),
                None,
            )

            if detection_decision is not None:
                detection_latency_ms = max(0, detection_decision.sim_time_ms - t_onset)
                if detection_latency_ms > window_ms:
                    false_negatives += 1
                    failure_reasons.append(
                        f"Detection latency ({detection_latency_ms}ms) exceeded "
                        f"required window ({window_ms}ms)."
                    )
                # Calculate safety margin percentage based on response timing
                remaining_window = max(0, window_ms - detection_latency_ms)
                safety_margin_pct = round(100.0 * (remaining_window / window_ms), 1)
            else:
                false_negatives += 1
                detection_latency_ms = None
                safety_margin_pct = 0.0
                failure_reasons.append("SIA Core failed to detect active hazard (False Negative).")

        # 3. Check physical envelope breaches and recovery
        if oracle_result.safety_envelope_breached:
            safety_margin_pct = -20.0
            failure_reasons.append("Safety envelope was breached (e.g. knockdown/capsize).")

        if self.config.require_recovery and not oracle_result.recovery_achieved:
            failure_reasons.append(
                "Vessel failed to achieve safe upright recovery at scenario completion."
            )

        if safety_margin_pct < self.config.min_safety_margin_pct and t_onset is not None:
            failure_reasons.append(
                f"Safety margin ({safety_margin_pct}%) was below minimum required threshold "
                f"({self.config.min_safety_margin_pct}%)."
            )

        # Verdict assignment
        verdict: Literal["PASS", "FAIL"] = "PASS" if not failure_reasons else "FAIL"

        if verdict == "PASS":
            notes = (
                f"PASS: Deterministic verification passed for {scenario_id}. "
                f"Latency: {detection_latency_ms}ms, Margin: {safety_margin_pct}%, "
                f"FP: {false_positives}, FN: {false_negatives}."
            )
        else:
            notes = f"FAIL: {scenario_id} failed verification. Reasons: " + "; ".join(
                failure_reasons
            )

        return EvaluationResult(
            scenario_id=scenario_id,
            run_id=run_id,
            verdict=verdict,
            detection_latency_ms=detection_latency_ms,
            false_positives=false_positives,
            false_negatives=false_negatives,
            safety_margin_pct=safety_margin_pct,
            notes=notes,
        )
