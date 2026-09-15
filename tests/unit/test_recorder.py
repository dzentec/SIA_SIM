"""Unit tests for RunRecorder and telemetry export (Plan 05-03)."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
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
    CandidateResponse,
    DecisionPayload,
    RiskAssessment,
)
from sia_sim.recorder.run_recorder import RunRecorder, SimulationRecord


def _make_dummy_data(
    tick: int,
    has_hazard: bool = False,
    has_null_sensors: bool = False,
) -> tuple[GroundTruthFrame, SensorFrame, DecisionPayload]:
    """Helper to generate consistent test frames for a given tick."""
    sim_time_ms = tick * 10

    gt = GroundTruthFrame(
        sim_time_ms=sim_time_ms,
        sequence_number=tick,
        vessel=VesselState(
            x_m=float(tick * 1.5),
            y_m=float(tick * 0.2),
            heading_deg=45.0,
            sog_m_s=6.5,
            cog_deg=46.0,
            heel_deg=12.0 if not has_hazard else 35.0,
            pitch_deg=1.5,
            roll_rate_deg_s=0.5 if not has_hazard else 15.0,
            yaw_rate_deg_s=0.2,
            rudder_angle_deg=0.0,
        ),
        environment=EnvironmentState(
            true_wind_speed_m_s=12.0,
            true_wind_angle_deg=135.0,
            wave_height_m=1.8,
            wave_period_s=6.0,
            current_speed_m_s=0.5,
            current_direction_deg=90.0,
        ),
        active_event_ids=("WAVE_GUST",) if has_hazard else (),
    )

    sf = SensorFrame(
        sim_time_ms=sim_time_ms,
        sequence_number=tick,
        imu=IMUReading(
            roll_deg=None if has_null_sensors else (12.0 if not has_hazard else 35.0),
            pitch_deg=1.5,
            roll_rate_deg_s=None if has_null_sensors else (0.5 if not has_hazard else 15.0),
            pitch_rate_deg_s=0.1,
            yaw_rate_deg_s=0.2,
            accel_x_m_s2=0.0,
            accel_y_m_s2=0.1,
            accel_z_m_s2=9.81,
            fault=False,
        ),
        gps=GPSReading(
            latitude_deg=None if has_null_sensors else 54.1234,
            longitude_deg=None if has_null_sensors else 10.5678,
            sog_kt=12.5,
            cog_deg=46.0,
            hdop=1.0,
            fault=False,
        ),
        wind=WindReading(
            apparent_wind_speed_kt=25.0,
            apparent_wind_angle_deg=140.0,
            fault=False,
        ),
        actuators=ActuatorState(
            rudder_angle_deg=0.0,
            mainsheet_pct=None,  # Standard yacht has no winch sensor
            fault=False,
        ),
    )

    if has_hazard:
        risk = RiskAssessment(
            hazard_id="BROACH_PRECURSOR",
            risk_score=0.85,
            confidence=0.9,
            evidence_ids=("imu.roll_deg", "imu.roll_rate_deg_s"),
        )
        c1 = CandidateResponse(
            response_id="RESP_01",
            action_type="BEAR_AWAY",
            rudder_command_deg=15.0,
            sail_command_pct=None,
            priority_score=0.9,
            rule_ids=("R_BROACH_01",),
        )
        c2 = CandidateResponse(
            response_id="RESP_02",
            action_type="EASE_SHEETS",
            rudder_command_deg=None,
            sail_command_pct=100.0,
            priority_score=0.7,
            rule_ids=("R_BROACH_02",),
        )
        decision = DecisionPayload(
            decision_id=f"DEC_{tick}",
            sim_time_ms=sim_time_ms,
            sensor_frame_sequence=tick,
            risk_assessment=risk,
            candidates=(c1, c2),
            selected_response=c1,
            conflict_resolution_note="Highest priority recovery action selected",
        )
    else:
        risk = RiskAssessment(
            hazard_id=None,
            risk_score=0.0,
            confidence=1.0,
            evidence_ids=(),
        )
        decision = DecisionPayload(
            decision_id=f"DEC_{tick}",
            sim_time_ms=sim_time_ms,
            sensor_frame_sequence=tick,
            risk_assessment=risk,
            candidates=(),
            selected_response=None,
            conflict_resolution_note="No hazard detected",
        )

    return gt, sf, decision


def test_empty_recorder_to_polars() -> None:
    """Empty recorder must return 3 valid empty DataFrames with correct schemas."""
    rec = RunRecorder()
    assert len(rec) == 0

    df_gt, df_sf, df_dec = rec.to_polars()
    assert isinstance(df_gt, pl.DataFrame)
    assert isinstance(df_sf, pl.DataFrame)
    assert isinstance(df_dec, pl.DataFrame)

    assert len(df_gt) == 0
    assert len(df_sf) == 0
    assert len(df_dec) == 0

    assert "sim_time_ms" in df_gt.columns
    assert "x_m" in df_gt.columns
    assert "imu_roll_deg" in df_sf.columns
    assert "risk_score" in df_dec.columns


def test_recorder_ingestion_and_polars_conversion() -> None:
    """Ingest 1000 ticks of 100 Hz simulation data and verify DataFrame conversion."""
    rec = RunRecorder()

    for tick in range(1000):
        has_hazard = 400 <= tick <= 600
        has_null = tick % 10 == 0
        gt, sf, dec = _make_dummy_data(tick, has_hazard=has_hazard, has_null_sensors=has_null)
        rec.record(gt, sf, dec)

    assert len(rec) == 1000
    assert len(rec.records) == 1000
    assert isinstance(rec.records[0], SimulationRecord)

    df_gt, df_sf, df_dec = rec.to_polars()

    assert len(df_gt) == 1000
    assert len(df_sf) == 1000
    assert len(df_dec) == 1000

    # Ground truth checks
    assert df_gt["sim_time_ms"].to_list() == [i * 10 for i in range(1000)]
    assert df_gt["sequence_number"].to_list() == list(range(1000))
    assert df_gt["heel_deg"].max() == 35.0

    # Sensor checks & Null preservation
    assert df_sf["actuators_mainsheet_pct"].null_count() == 1000
    assert df_sf["imu_roll_deg"].null_count() == 100  # Every 10th tick was null
    assert df_sf["gps_latitude_deg"].null_count() == 100

    # Decision checks
    assert df_dec["risk_score"].max() == pytest.approx(0.85)
    assert df_dec["hazard_id"].null_count() == 1000 - 201  # 201 hazard ticks (400..600 inclusive)
    assert df_dec.filter(pl.col("hazard_id") == "BROACH_PRECURSOR").height == 201


def test_data_boundary_isolation() -> None:
    """Ensure strict architectural boundary: df_sensor must NEVER have Ground Truth columns."""
    rec = RunRecorder()
    gt, sf, dec = _make_dummy_data(0)
    rec.record(gt, sf, dec)

    _df_gt, df_sf, df_dec = rec.to_polars()

    # Ground truth specific fields
    gt_specific_fields = {
        "x_m",
        "y_m",
        "heading_deg",
        "true_wind_speed_m_s",
        "true_wind_angle_deg",
        "wave_height_m",
        "wave_period_s",
        "current_speed_m_s",
        "current_direction_deg",
        "active_event_ids",
    }

    # Verify none of these appear in df_sensor
    for field in gt_specific_fields:
        assert field not in df_sf.columns, f"Boundary violation: {field} leaked into df_sensor"

    # Verify df_decisions only has decision-related fields
    for field in gt_specific_fields:
        assert field not in df_dec.columns, f"Boundary violation: {field} leaked into df_decisions"


def test_jsonl_export_and_roundtrip(tmp_path: Path) -> None:
    """Verify JSON Lines export produces valid parseable JSON records."""
    rec = RunRecorder()
    for tick in range(10):
        gt, sf, dec = _make_dummy_data(tick, has_hazard=(tick > 5))
        rec.record(gt, sf, dec)

    jsonl_path = tmp_path / "telemetry" / "run_01.jsonl"
    rec.to_jsonl(jsonl_path)

    assert jsonl_path.exists()

    with open(jsonl_path, encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 10

    for i, line in enumerate(lines):
        data = json.loads(line)
        assert "ground_truth" in data
        assert "sensor_frame" in data
        assert "decision" in data
        assert data["ground_truth"]["sequence_number"] == i
        assert data["sensor_frame"]["sequence_number"] == i
        assert data["decision"]["sensor_frame_sequence"] == i


def test_recorder_reset() -> None:
    """Verify reset clears all recorded history."""
    rec = RunRecorder()
    gt, sf, dec = _make_dummy_data(0)
    rec.record(gt, sf, dec)
    assert len(rec) == 1

    rec.reset()
    assert len(rec) == 0
    assert len(rec.records) == 0

    df_gt, df_sf, df_dec = rec.to_polars()
    assert len(df_gt) == 0
    assert len(df_sf) == 0
    assert len(df_dec) == 0
