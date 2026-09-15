"""Decision and evaluation contract models for SIA Simulation.

Covers:
1. DecisionPayload — output of SIA Core (risk assessment, candidate responses, selected response).
2. OracleResult — independent ground-truth evaluation from Oracle (INV-03).
3. EvaluationResult — objective PASS/FAIL comparison from Evaluator (INV-08).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskAssessment(BaseModel):
    """SIA Core risk assessment for the current sensor frame."""

    model_config = ConfigDict(frozen=True, strict=True)

    hazard_id: str | None
    """Identified hazard identifier, or None if no hazard detected."""

    risk_score: float = Field(ge=0.0, le=1.0)
    """Assessed risk score from 0.0 (safe) to 1.0 (critical danger)."""

    confidence: float = Field(ge=0.0, le=1.0)
    """Confidence in assessment from 0.0 (no confidence) to 1.0 (certain)."""

    evidence_ids: tuple[str, ...]
    """IDs/names of sensor channels or observations driving this assessment."""


class CandidateResponse(BaseModel):
    """One candidate response proposed by SIA Core rules or algorithms."""

    model_config = ConfigDict(frozen=True, strict=True)

    response_id: str
    """Unique identifier for this candidate response."""

    action_type: str
    """Action category, e.g. 'REDUCE_SAIL', 'ALTER_COURSE', 'ALERT_CREW', 'RUDDER_CORRECTION'."""

    rudder_command_deg: float | None
    """Commanded rudder angle in degrees. None = no rudder command."""

    sail_command_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    """Commanded sail trim percentage (0-100%). None = no sail command."""

    priority_score: float
    """Priority/preference score (higher score = preferred response)."""

    rule_ids: tuple[str, ...]
    """SIA rule identifiers that generated this candidate response."""


class DecisionPayload(BaseModel):
    """Complete SIA Core decision output for one sensor frame.

    Contains risk assessment, up to 3 candidate responses (per 3-response architecture),
    and the selected response after conflict resolution.

    Output of SIACore.process(frame: SensorFrame).
    """

    model_config = ConfigDict(frozen=True, strict=True)

    decision_id: str
    """Unique decision identifier."""

    sim_time_ms: int = Field(ge=0)
    """Simulation timestamp at decision time in integer milliseconds."""

    sensor_frame_sequence: int = Field(ge=0)
    """Sequence number of the input SensorFrame that triggered this decision."""

    risk_assessment: RiskAssessment
    """Risk evaluation result."""

    candidates: tuple[CandidateResponse, ...] = Field(max_length=3)
    """Up to 3 candidate responses evaluated during this decision cycle."""

    selected_response: CandidateResponse | None
    """Chosen candidate response after conflict resolution, or None if no action taken."""

    conflict_resolution_note: str
    """Explanation of candidate selection and conflict resolution logic for audit trail."""


class OracleResult(BaseModel):
    """Independent oracle verdict based strictly on ground truth data.

    Architectural invariants:
      INV-03: Oracle does not use SIA decision to construct expected result.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    scenario_id: str
    """Scenario identifier evaluated."""

    hazard_onset_ms: int | None
    """Simulation time when hazard threshold was first breached in ground truth.
    None if no hazard.
    """

    required_response_window_ms: int | None
    """Maximum allowed response time in ms from hazard onset. None if no hazard."""

    expected_action_type: str | None
    """Ideal recovery action type according to physics/domain rules. None if no action needed."""

    recovery_achieved: bool
    """True if physical recovery conditions were satisfied before safety envelope breach."""

    safety_envelope_breached: bool
    """True if hard physical safety limits were exceeded (e.g. knockdown, capsize)."""

    severity: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    """Maximum severity level reached during the scenario."""


class EvaluationResult(BaseModel):
    """Objective PASS/FAIL evaluation comparing SIA Core decisions against Oracle expectations.

    Architectural invariants:
      INV-08: Evaluator observes; it does not correct SIA output.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    scenario_id: str
    """Scenario identifier evaluated."""

    run_id: str
    """Unique identifier for this evaluation run."""

    verdict: Literal["PASS", "FAIL"]
    """Objective test verdict."""

    detection_latency_ms: int | None
    """Time in ms from ground truth hazard onset to SIA detection/response. None if undetected."""

    false_positives: int = Field(ge=0)
    """Count of alert actions taken when no hazard condition existed."""

    false_negatives: int = Field(ge=0)
    """Count of unmitigated hazard events."""

    safety_margin_pct: float
    """Safety margin percentage remaining at time of SIA response
    (negative if envelope breached).
    """

    notes: str
    """Human-readable evaluation notes and diagnostic summary."""
