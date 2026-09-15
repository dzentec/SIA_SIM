"""Unit tests for MockSIA rule evaluation, risk assessment, and candidate responses."""

from __future__ import annotations

from sia_sim.contracts.data import (
    ActuatorState,
    GPSReading,
    IMUReading,
    SensorFrame,
    WindReading,
)
from sia_sim.sia.mock_sia import MockSIA
from sia_sim.sia.protocol import SIACore


def make_frame(
    t_ms: int = 0,
    roll_deg: float = 5.0,
    roll_rate_deg_s: float = 0.0,
    yaw_rate_deg_s: float = 0.0,
    rudder_angle_deg: float = 0.0,
    imu_fault: bool = False,
    gps_fault: bool = False,
) -> SensorFrame:
    return SensorFrame(
        sim_time_ms=t_ms,
        imu=IMUReading(
            roll_deg=None if imu_fault else roll_deg,
            pitch_deg=None if imu_fault else 1.0,
            roll_rate_deg_s=None if imu_fault else roll_rate_deg_s,
            pitch_rate_deg_s=None if imu_fault else 0.0,
            yaw_rate_deg_s=None if imu_fault else yaw_rate_deg_s,
            accel_x_m_s2=None if imu_fault else 0.0,
            accel_y_m_s2=None if imu_fault else 1.0,
            accel_z_m_s2=None if imu_fault else 9.8,
            fault=imu_fault,
        ),
        gps=GPSReading(
            latitude_deg=None if gps_fault else 43.5,
            longitude_deg=None if gps_fault else 16.4,
            sog_kt=None if gps_fault else 6.0,
            cog_deg=None if gps_fault else 45.0,
            hdop=None if gps_fault else 1.0,
            fault=gps_fault,
        ),
        wind=WindReading(
            apparent_wind_speed_kt=18.0,
            apparent_wind_angle_deg=50.0,
            fault=False,
        ),
        actuators=ActuatorState(
            rudder_angle_deg=rudder_angle_deg,
            mainsheet_pct=None,
            fault=False,
        ),
        sequence_number=t_ms // 10,
    )


class TestMockSIA:
    def test_implements_siacore_protocol(self) -> None:
        engine = MockSIA()
        assert isinstance(engine, SIACore)

    def test_nominal_conditions_produces_zero_candidates(self) -> None:
        engine = MockSIA()
        frame = make_frame(0, roll_deg=5.0)

        decision = engine.process(frame)
        assert decision.risk_assessment.hazard_id is None
        assert decision.risk_assessment.risk_score == 0.0
        assert decision.risk_assessment.confidence == 1.0
        assert len(decision.candidates) == 0
        assert decision.selected_response is None

    def test_advisory_heel_generates_one_candidate(self) -> None:
        engine = MockSIA()
        frame = make_frame(1000, roll_deg=23.0)

        decision = engine.process(frame)
        assert decision.risk_assessment.hazard_id == "HAZ-HEEL-ADVISORY"
        assert decision.risk_assessment.risk_score > 0.3
        assert len(decision.candidates) == 1
        assert decision.selected_response is not None
        assert decision.selected_response.action_type == "REDUCE_SAIL"

    def test_critical_broach_precursor_generates_three_candidates(self) -> None:
        engine = MockSIA()
        frame = make_frame(
            2000,
            roll_deg=32.0,
            roll_rate_deg_s=8.0,
            yaw_rate_deg_s=3.5,
            rudder_angle_deg=0.0,
        )

        decision = engine.process(frame)
        assert decision.risk_assessment.hazard_id == "HAZ-BROACH-PRECURSOR"
        assert decision.risk_assessment.risk_score >= 0.7
        # 3-response architecture check
        assert len(decision.candidates) == 3

        # Assert candidate types
        action_types = {c.action_type for c in decision.candidates}
        assert action_types == {"REDUCE_SAIL", "RUDDER_CORRECTION", "ALTER_COURSE"}

        # Conflict resolution selects highest priority (depower sail)
        assert decision.selected_response is not None
        assert decision.selected_response.action_type == "REDUCE_SAIL"

    def test_sensor_fault_degrades_confidence(self) -> None:
        engine = MockSIA()
        frame_faulty = make_frame(0, roll_deg=10.0, imu_fault=True, gps_fault=True)

        decision = engine.process(frame_faulty)
        # Confidence should be reduced from 1.0 due to IMU and GPS faults
        assert decision.risk_assessment.confidence <= 0.5
        assert "IMU_DEGRADED" in decision.risk_assessment.evidence_ids
        assert "GPS_DEGRADED" in decision.risk_assessment.evidence_ids

    def test_deterministic_repeatability(self) -> None:
        e1 = MockSIA()
        e2 = MockSIA()

        frames = [make_frame(t, roll_deg=10.0 + t * 0.1) for t in range(0, 500, 10)]

        d1 = [e1.process(f) for f in frames]
        d2 = [e2.process(f) for f in frames]

        assert d1 == d2
