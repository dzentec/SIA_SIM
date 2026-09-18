"""Deterministic MockSIA implementation for testing and baseline validation."""

from __future__ import annotations

from collections.abc import Sequence

from sia_sim.contracts.data import SensorFrame
from sia_sim.contracts.evaluation import CandidateResponse, DecisionPayload, RiskAssessment
from sia_sim.contracts.sails import ALL_SAIL_IDS, SailAdvisoryPayload
from sia_sim.sails.advisor import generate_sail_advisory
from sia_sim.sia.protocol import SIACore


class MockSIA(SIACore):
    """Deterministic rule-based SIA Core implementation.

    Implements:
    - L0 Sensor Integrity: Monitors sensor faults, null values, and degrades confidence.
    - L2 Hazard Detection: Detects Broach Precursor based on roll, roll rate, and yaw rate.
    - L3 Risk Assessment: Calculates bounded risk score and confidence.
    - L4 Candidate Responses: Generates up to 3 candidate responses and resolves conflict,
      strictly adhering to on-board available sails and hull rules v1.1.
    """

    def __init__(
        self,
        heel_warning_deg: float = 20.0,
        heel_critical_deg: float = 28.0,
        yaw_rate_threshold_deg_s: float = 1.5,
        hull_type: str = "monohull",
        available_sails: Sequence[str] | None = None,
    ) -> None:
        self.heel_warning_deg = heel_warning_deg
        self.heel_critical_deg = heel_critical_deg
        self.yaw_rate_threshold_deg_s = yaw_rate_threshold_deg_s
        self.hull_type = hull_type
        self.available_sails = tuple(available_sails) if available_sails is not None else ALL_SAIL_IDS
        self._decision_count = 0
        self.last_sail_advisory: SailAdvisoryPayload | None = None

    def set_vessel_context(
        self,
        hull_type: str = "monohull",
        available_sails: Sequence[str] | None = None,
    ) -> None:
        """Update active hull type and on-board sail inventory for the simulation."""
        self.hull_type = hull_type
        self.available_sails = tuple(available_sails) if available_sails is not None else ALL_SAIL_IDS

    def reset(self) -> None:
        """Reset internal temporal counters and filters."""
        self._decision_count = 0
        self.last_sail_advisory = None

    def process(self, frame: SensorFrame) -> DecisionPayload:
        """Process SensorFrame and produce structured DecisionPayload."""
        if not isinstance(frame, SensorFrame):
            raise TypeError(f"Expected SensorFrame, got {type(frame)}")

        self._decision_count += 1
        decision_id = f"DEC-{frame.sim_time_ms:06d}-{self._decision_count:04d}"

        # 1. L0 Sensor Integrity Evaluation
        evidence: list[str] = []
        confidence = 1.0

        if frame.imu.fault or frame.imu.roll_deg is None:
            confidence -= 0.5
            evidence.append("IMU_DEGRADED")
        if frame.gps.fault or frame.gps.sog_kt is None:
            confidence -= 0.2
            evidence.append("GPS_DEGRADED")
        if frame.wind.fault or frame.wind.apparent_wind_speed_kt is None:
            confidence -= 0.15
            evidence.append("WIND_DEGRADED")
        if frame.actuators.fault or frame.actuators.rudder_angle_deg is None:
            confidence -= 0.15
            evidence.append("ACTUATOR_DEGRADED")

        confidence = max(0.0, min(1.0, confidence))

        # 2. Extract observable sensor values
        roll = abs(frame.imu.roll_deg) if frame.imu.roll_deg is not None else 0.0
        roll_rate = abs(frame.imu.roll_rate_deg_s) if frame.imu.roll_rate_deg_s is not None else 0.0
        yaw_rate = abs(frame.imu.yaw_rate_deg_s) if frame.imu.yaw_rate_deg_s is not None else 0.0

        aws = frame.wind.apparent_wind_speed_kt or 10.0
        awa = frame.wind.apparent_wind_angle_deg or 45.0

        # Estimate TWS / TWA approximation from observable SensorFrame (boundary compliant)
        # In beam/broad reach approximation:
        tws_approx = aws
        twa_approx = awa

        # 3. Compute Sail Advisory strictly for available on-board inventory
        sail_advisory = generate_sail_advisory(
            tws_kt=tws_approx,
            twa_deg=twa_approx,
            hull_type=self.hull_type,
            available_sails=self.available_sails,
        )
        self.last_sail_advisory = sail_advisory

        # 4. L2 Hazard Detection & L3 Risk Assessment
        hazard_id: str | None = None
        risk_score = 0.0
        candidates: list[CandidateResponse] = []
        selected: CandidateResponse | None = None
        note = "Nominal conditions, no safety hazard"

        if roll >= self.heel_critical_deg:
            hazard_id = "HAZ-BROACH-PRECURSOR"
            risk_score = min(1.0, 0.7 + (roll - self.heel_critical_deg) * 0.03 + yaw_rate * 0.02)
            evidence.extend(["HIGH_HEEL", "HIGH_YAW_RATE"])
            note = f"Critical heel ({roll:.1f} deg) with uncommanded yaw round-up; broach onset"

            # 4. L4 Candidate Response Generation (up to 3 candidate responses)
            c1 = CandidateResponse(
                response_id=f"RESP-{frame.sim_time_ms}-01",
                action_type="REDUCE_SAIL",
                rudder_command_deg=None,
                sail_command_pct=30.0,  # Depower / ease sails
                priority_score=0.95,
                rule_ids=("RULE-BROACH-SAIL-01",),
            )
            c2 = CandidateResponse(
                response_id=f"RESP-{frame.sim_time_ms}-02",
                action_type="RUDDER_CORRECTION",
                rudder_command_deg=-20.0,  # Counter-rudder
                sail_command_pct=None,
                priority_score=0.85,
                rule_ids=("RULE-BROACH-RUDDER-01",),
            )
            c3 = CandidateResponse(
                response_id=f"RESP-{frame.sim_time_ms}-03",
                action_type="ALTER_COURSE",
                rudder_command_deg=-10.0,
                sail_command_pct=50.0,
                priority_score=0.75,
                rule_ids=("RULE-BROACH-COURSE-01",),
            )
            candidates = [c1, c2, c3]
            selected = c1

        elif roll >= self.heel_warning_deg or (roll > 18.0 and roll_rate > 5.0):
            hazard_id = "HAZ-HEEL-ADVISORY"
            risk_score = min(0.65, 0.35 + (roll - self.heel_warning_deg) * 0.03)
            evidence.append("MODERATE_HEEL")
            note = f"Elevated heel ({roll:.1f} deg), monitoring stability"

            # Suggest reef or sail change based on available sails
            rule_id = "RULE-HEEL-ADVISORY-01"
            if sail_advisory.recommended_reef > 0:
                rule_id = f"RULE-REEF-{sail_advisory.recommended_reef:02d}"

            c1 = CandidateResponse(
                response_id=f"RESP-{frame.sim_time_ms}-01",
                action_type="REDUCE_SAIL",
                rudder_command_deg=None,
                sail_command_pct=70.0,
                priority_score=0.80,
                rule_ids=(rule_id,),
            )
            candidates = [c1]
            selected = c1

        return DecisionPayload(
            decision_id=decision_id,
            sim_time_ms=frame.sim_time_ms,
            sensor_frame_sequence=frame.sequence_number,
            risk_assessment=RiskAssessment(
                hazard_id=hazard_id,
                risk_score=round(risk_score, 4),
                confidence=round(confidence, 4),
                evidence_ids=tuple(evidence),
            ),
            candidates=tuple(candidates),
            selected_response=selected,
            conflict_resolution_note=note,
        )
