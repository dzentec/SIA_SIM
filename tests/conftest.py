"""Pytest configuration and shared fixtures for SIA Simulation."""

from __future__ import annotations

import pytest

from sia_sim.contracts.data import (
    ActuatorState,
    EnvironmentState,
    GPSReading,
    GroundTruthFrame,
    IMUReading,
    SensorFrame,
    VesselState,
    WindReading,
)
from sia_sim.contracts.evaluation import (
    DecisionPayload,
    EvaluationResult,
    OracleResult,
    RiskAssessment,
)
from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig


@pytest.fixture
def default_seed() -> int:
    return 42


@pytest.fixture
def minimal_imu_all_failed() -> IMUReading:
    return IMUReading(
        roll_deg=None,
        pitch_deg=None,
        roll_rate_deg_s=None,
        pitch_rate_deg_s=None,
        yaw_rate_deg_s=None,
        accel_x_m_s2=None,
        accel_y_m_s2=None,
        accel_z_m_s2=None,
        fault=True,
    )


@pytest.fixture
def minimal_gps_no_fix() -> GPSReading:
    return GPSReading(
        latitude_deg=None,
        longitude_deg=None,
        sog_kt=None,
        cog_deg=None,
        hdop=None,
        fault=True,
    )


@pytest.fixture
def minimal_wind_failed() -> WindReading:
    return WindReading(
        apparent_wind_speed_kt=None,
        apparent_wind_angle_deg=None,
        fault=True,
    )


@pytest.fixture
def minimal_actuators_no_feedback() -> ActuatorState:
    return ActuatorState(
        rudder_angle_deg=None,
        mainsheet_pct=None,
        fault=True,
    )


@pytest.fixture
def minimal_sensor_frame(
    minimal_imu_all_failed: IMUReading,
    minimal_gps_no_fix: GPSReading,
    minimal_wind_failed: WindReading,
    minimal_actuators_no_feedback: ActuatorState,
) -> SensorFrame:
    return SensorFrame(
        sim_time_ms=0,
        imu=minimal_imu_all_failed,
        gps=minimal_gps_no_fix,
        wind=minimal_wind_failed,
        actuators=minimal_actuators_no_feedback,
        sequence_number=0,
    )


@pytest.fixture
def minimal_sensor_frame_healthy() -> SensorFrame:
    return SensorFrame(
        sim_time_ms=10,
        imu=IMUReading(
            roll_deg=15.0,
            pitch_deg=2.5,
            roll_rate_deg_s=3.0,
            pitch_rate_deg_s=0.5,
            yaw_rate_deg_s=-1.0,
            accel_x_m_s2=0.1,
            accel_y_m_s2=9.8,
            accel_z_m_s2=0.05,
            fault=False,
        ),
        gps=GPSReading(
            latitude_deg=59.3293,
            longitude_deg=18.0686,
            sog_kt=5.8,
            cog_deg=45.0,
            hdop=1.2,
            fault=False,
        ),
        wind=WindReading(
            apparent_wind_speed_kt=20.5,
            apparent_wind_angle_deg=-35.0,
            fault=False,
        ),
        actuators=ActuatorState(
            rudder_angle_deg=5.0,
            mainsheet_pct=75.0,
            fault=False,
        ),
        sequence_number=1,
    )


@pytest.fixture
def minimal_ground_truth_frame() -> GroundTruthFrame:
    return GroundTruthFrame(
        sim_time_ms=0,
        vessel=VesselState(
            x_m=0.0,
            y_m=0.0,
            heading_deg=45.0,
            sog_m_s=3.0,
            cog_deg=47.0,
            heel_deg=15.0,
            pitch_deg=2.0,
            roll_rate_deg_s=1.5,
            yaw_rate_deg_s=-0.5,
            rudder_angle_deg=3.0,
        ),
        environment=EnvironmentState(
            true_wind_speed_m_s=10.3,
            true_wind_angle_deg=200.0,
            wave_height_m=3.0,
            wave_period_s=7.0,
            current_speed_m_s=0.5,
            current_direction_deg=90.0,
        ),
        sequence_number=0,
        active_event_ids=(),
    )


@pytest.fixture
def minimal_scenario() -> Scenario:
    return Scenario(
        scenario_id="SIM-005",
        scenario_version="1.0.0",
        name="Broach Precursor",
        description="Single event scenario for testing",
        duration_ms=20000,
        seed=42,
        vessel=VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heel_deg=15.0,
            initial_heading_deg=65.0,
            initial_sog_kt=5.8,
        ),
        events=(
            ScenarioEvent(
                sim_time_ms=10000,
                event_id="EVT-001",
                event_type="wave_impact",
                parameters={"height_m": 3.0},
            ),
        ),
        initial_tws_kt=20.0,
        initial_twa_deg=65.0,
        initial_wave_height_m=3.0,
        initial_wave_period_s=7.0,
    )


@pytest.fixture
def minimal_decision_payload() -> DecisionPayload:
    return DecisionPayload(
        decision_id="DEC-000000",
        sim_time_ms=0,
        sensor_frame_sequence=0,
        risk_assessment=RiskAssessment(
            hazard_id=None,
            risk_score=0.0,
            confidence=1.0,
            evidence_ids=(),
        ),
        candidates=(),
        selected_response=None,
        conflict_resolution_note="Initial nominal state, no response required.",
    )


@pytest.fixture
def minimal_oracle_result_no_hazard() -> OracleResult:
    return OracleResult(
        scenario_id="SIM-001",
        hazard_onset_ms=None,
        required_response_window_ms=None,
        expected_action_type=None,
        recovery_achieved=True,
        safety_envelope_breached=False,
        severity="NONE",
    )


@pytest.fixture
def minimal_evaluation_result_pass() -> EvaluationResult:
    return EvaluationResult(
        scenario_id="SIM-005",
        run_id="RUN-001",
        verdict="PASS",
        detection_latency_ms=300,
        false_positives=0,
        false_negatives=0,
        safety_margin_pct=85.0,
        notes="Nominal pass",
    )
