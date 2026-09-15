"""Independent Ground-Truth Safety Oracle for SIA Simulation.

Architectural Invariant INV-03:
The Oracle evaluates physical state strictly from GroundTruthFrame and scenario
definitions without inspecting or relying on SIA Core decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sia_sim.contracts.data import GroundTruthFrame
from sia_sim.contracts.evaluation import OracleResult


@dataclass(frozen=True)
class OracleConfig:
    """Configuration parameters for ground truth safety evaluation."""

    heel_hazard_deg: float = 25.0
    """Heel angle (degrees) indicating onset of broach hazard."""

    heel_critical_deg: float = 50.0
    """Heel angle (degrees) indicating safety envelope breach (knockdown)."""

    yaw_rate_hazard_deg_s: float = 2.0
    """Uncommanded yaw rate (deg/s) indicating broach round-up into the wind."""

    max_allowed_response_window_ms: int = 3000
    """Maximum response window (ms) from hazard onset before broach becomes unrecoverable."""

    recovery_heel_deg: float = 20.0
    """Maximum heel angle for verifying recovery at end of scenario."""

    recovery_yaw_rate_deg_s: float = 3.0
    """Maximum yaw rate for verifying recovery at end of scenario."""


class SafetyOracle:
    """Evaluates ground-truth vessel dynamics to produce objective safety benchmarks."""

    def __init__(self, config: OracleConfig | None = None) -> None:
        self.config = config or OracleConfig()

    def evaluate(
        self,
        ground_truth_frames: Sequence[GroundTruthFrame],
        scenario_id: str = "SIM-005",
    ) -> OracleResult:
        """Evaluates a full sequence of GroundTruthFrames and produces an OracleResult."""
        if not ground_truth_frames:
            return OracleResult(
                scenario_id=scenario_id,
                hazard_onset_ms=None,
                required_response_window_ms=None,
                expected_action_type=None,
                recovery_achieved=True,
                safety_envelope_breached=False,
                severity="NONE",
            )

        hazard_onset_ms: int | None = None
        safety_envelope_breached = False
        max_severity: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = "NONE"

        max_heel = 0.0
        max_yaw_rate = 0.0

        for frame in ground_truth_frames:
            vessel = frame.vessel
            heel = abs(vessel.heel_deg)
            yaw_rate = abs(vessel.yaw_rate_deg_s)

            if heel > max_heel:
                max_heel = heel
            if yaw_rate > max_yaw_rate:
                max_yaw_rate = yaw_rate

            # Check safety envelope breach
            if heel >= self.config.heel_critical_deg:
                safety_envelope_breached = True

            # Detect hazard onset: broach precursor is characterized by severe heel
            # combined with yaw rate or high heel (>=30 deg)
            is_hazard = (
                heel >= self.config.heel_hazard_deg
                and yaw_rate >= self.config.yaw_rate_hazard_deg_s
            ) or heel >= 30.0

            if is_hazard and hazard_onset_ms is None:
                hazard_onset_ms = frame.sim_time_ms

        # Determine overall scenario severity
        if safety_envelope_breached or max_heel >= 35.0:
            max_severity = "CRITICAL"
        elif (
            max_heel >= self.config.heel_hazard_deg
            or max_yaw_rate >= self.config.yaw_rate_hazard_deg_s
        ):
            max_severity = "HIGH"
        elif max_heel >= 18.0:
            max_severity = "MEDIUM"
        elif max_heel >= 10.0:
            max_severity = "LOW"
        else:
            max_severity = "NONE"

        # Determine expected action type and response window if hazard was present
        if hazard_onset_ms is not None:
            expected_action_type = "EASE_MAIN"
            required_response_window_ms = self.config.max_allowed_response_window_ms
        else:
            expected_action_type = None
            required_response_window_ms = None

        # Check recovery state on final window (last 10% of frames)
        if hazard_onset_ms is None:
            recovery_achieved = not safety_envelope_breached
        else:
            tail_count = max(1, len(ground_truth_frames) // 10)
            final_frames = ground_truth_frames[-tail_count:]
            final_heel_ok = all(
                abs(f.vessel.heel_deg) <= self.config.recovery_heel_deg for f in final_frames
            )
            final_yaw_ok = all(
                abs(f.vessel.yaw_rate_deg_s) <= self.config.recovery_yaw_rate_deg_s
                for f in final_frames
            )
            recovery_achieved = (not safety_envelope_breached) and final_heel_ok and final_yaw_ok

        return OracleResult(
            scenario_id=scenario_id,
            hazard_onset_ms=hazard_onset_ms,
            required_response_window_ms=required_response_window_ms,
            expected_action_type=expected_action_type,
            recovery_achieved=recovery_achieved,
            safety_envelope_breached=safety_envelope_breached,
            severity=max_severity,
        )

    def reset(self) -> None:
        """Resets any stateful tracking for a new evaluation run."""
        pass
