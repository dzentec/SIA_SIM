"""High-frequency run recorder for simulation telemetry and SIA Core decisions.

Captures paired (GroundTruthFrame, SensorFrame, DecisionPayload) at 100 Hz,
providing fast in-memory storage, Polars DataFrame conversion, and zero-copy trace export.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from sia_sim.contracts.data import GroundTruthFrame, SensorFrame
from sia_sim.contracts.evaluation import DecisionPayload, EvaluationResult, OracleResult

SchemaDict = Mapping[str, type[pl.DataType] | pl.DataType]

GROUND_TRUTH_SCHEMA: SchemaDict = {
    "sim_time_ms": pl.Int64,
    "sequence_number": pl.Int64,
    "x_m": pl.Float64,
    "y_m": pl.Float64,
    "heading_deg": pl.Float64,
    "sog_m_s": pl.Float64,
    "cog_deg": pl.Float64,
    "heel_deg": pl.Float64,
    "pitch_deg": pl.Float64,
    "roll_rate_deg_s": pl.Float64,
    "yaw_rate_deg_s": pl.Float64,
    "rudder_angle_deg": pl.Float64,
    "true_wind_speed_m_s": pl.Float64,
    "true_wind_angle_deg": pl.Float64,
    "wave_height_m": pl.Float64,
    "wave_period_s": pl.Float64,
    "current_speed_m_s": pl.Float64,
    "current_direction_deg": pl.Float64,
    "active_event_ids": pl.List(pl.Utf8),
}

SENSOR_SCHEMA: SchemaDict = {
    "sim_time_ms": pl.Int64,
    "sequence_number": pl.Int64,
    "imu_roll_deg": pl.Float64,
    "imu_pitch_deg": pl.Float64,
    "imu_roll_rate_deg_s": pl.Float64,
    "imu_pitch_rate_deg_s": pl.Float64,
    "imu_yaw_rate_deg_s": pl.Float64,
    "imu_accel_x_m_s2": pl.Float64,
    "imu_accel_y_m_s2": pl.Float64,
    "imu_accel_z_m_s2": pl.Float64,
    "imu_fault": pl.Boolean,
    "gps_latitude_deg": pl.Float64,
    "gps_longitude_deg": pl.Float64,
    "gps_sog_kt": pl.Float64,
    "gps_cog_deg": pl.Float64,
    "gps_hdop": pl.Float64,
    "gps_fault": pl.Boolean,
    "wind_apparent_wind_speed_kt": pl.Float64,
    "wind_apparent_wind_angle_deg": pl.Float64,
    "wind_fault": pl.Boolean,
    "actuators_rudder_angle_deg": pl.Float64,
    "actuators_mainsheet_pct": pl.Float64,
    "actuators_fault": pl.Boolean,
}

DECISIONS_SCHEMA: SchemaDict = {
    "sim_time_ms": pl.Int64,
    "decision_id": pl.Utf8,
    "sensor_frame_sequence": pl.Int64,
    "hazard_id": pl.Utf8,
    "risk_score": pl.Float64,
    "confidence": pl.Float64,
    "evidence_ids": pl.List(pl.Utf8),
    "num_candidates": pl.Int64,
    "selected_response_id": pl.Utf8,
    "selected_action_type": pl.Utf8,
    "selected_rudder_command_deg": pl.Float64,
    "selected_sail_command_pct": pl.Float64,
    "selected_priority_score": pl.Float64,
    "conflict_resolution_note": pl.Utf8,
}


@dataclass(frozen=True, slots=True)
class SimulationRecord:
    """One simulation tick's paired ground truth, sensor observations, and SIA decision."""

    gt: GroundTruthFrame
    sf: SensorFrame
    decision: DecisionPayload


class RunRecorder:
    """Synchronous 100 Hz simulation recorder.

    Stores ticks in-memory and converts them into separate Polars DataFrames or JSON Lines.
    Maintains strict boundary: df_sensor never includes Ground Truth fields.
    """

    def __init__(self) -> None:
        self._records: list[SimulationRecord] = []

    def record(
        self,
        gt: GroundTruthFrame,
        sf: SensorFrame,
        decision: DecisionPayload,
    ) -> None:
        """Record one tick of simulation data.

        Args:
            gt: GroundTruthFrame containing true physics/environment state.
            sf: SensorFrame containing degraded/observable sensor signals.
            decision: DecisionPayload containing SIA Core risk and advisory responses.
        """
        self._records.append(SimulationRecord(gt=gt, sf=sf, decision=decision))

    @property
    def records(self) -> tuple[SimulationRecord, ...]:
        """Return tuple of all captured simulation records."""
        return tuple(self._records)

    def __len__(self) -> int:
        """Return number of recorded ticks."""
        return len(self._records)

    def reset(self) -> None:
        """Clear all recorded data."""
        self._records.clear()

    def to_polars(self) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """Convert recorded simulation history into 3 separate Polars DataFrames.

        Returns:
            Tuple of (df_ground_truth, df_sensor, df_decisions).
        """
        if not self._records:
            return (
                pl.DataFrame(schema=GROUND_TRUTH_SCHEMA),
                pl.DataFrame(schema=SENSOR_SCHEMA),
                pl.DataFrame(schema=DECISIONS_SCHEMA),
            )

        gt_rows: list[dict[str, Any]] = []
        sf_rows: list[dict[str, Any]] = []
        dec_rows: list[dict[str, Any]] = []

        for rec in self._records:
            gt = rec.gt
            sf = rec.sf
            dec = rec.decision

            # Ground Truth row
            gt_rows.append(
                {
                    "sim_time_ms": gt.sim_time_ms,
                    "sequence_number": gt.sequence_number,
                    "x_m": gt.vessel.x_m,
                    "y_m": gt.vessel.y_m,
                    "heading_deg": gt.vessel.heading_deg,
                    "sog_m_s": gt.vessel.sog_m_s,
                    "cog_deg": gt.vessel.cog_deg,
                    "heel_deg": gt.vessel.heel_deg,
                    "pitch_deg": gt.vessel.pitch_deg,
                    "roll_rate_deg_s": gt.vessel.roll_rate_deg_s,
                    "yaw_rate_deg_s": gt.vessel.yaw_rate_deg_s,
                    "rudder_angle_deg": gt.vessel.rudder_angle_deg,
                    "true_wind_speed_m_s": gt.environment.true_wind_speed_m_s,
                    "true_wind_angle_deg": gt.environment.true_wind_angle_deg,
                    "wave_height_m": gt.environment.wave_height_m,
                    "wave_period_s": gt.environment.wave_period_s,
                    "current_speed_m_s": gt.environment.current_speed_m_s,
                    "current_direction_deg": gt.environment.current_direction_deg,
                    "active_event_ids": list(gt.active_event_ids),
                }
            )

            # Sensor Frame row (Strict isolation: only sensor channels)
            sf_rows.append(
                {
                    "sim_time_ms": sf.sim_time_ms,
                    "sequence_number": sf.sequence_number,
                    "imu_roll_deg": sf.imu.roll_deg,
                    "imu_pitch_deg": sf.imu.pitch_deg,
                    "imu_roll_rate_deg_s": sf.imu.roll_rate_deg_s,
                    "imu_pitch_rate_deg_s": sf.imu.pitch_rate_deg_s,
                    "imu_yaw_rate_deg_s": sf.imu.yaw_rate_deg_s,
                    "imu_accel_x_m_s2": sf.imu.accel_x_m_s2,
                    "imu_accel_y_m_s2": sf.imu.accel_y_m_s2,
                    "imu_accel_z_m_s2": sf.imu.accel_z_m_s2,
                    "imu_fault": sf.imu.fault,
                    "gps_latitude_deg": sf.gps.latitude_deg,
                    "gps_longitude_deg": sf.gps.longitude_deg,
                    "gps_sog_kt": sf.gps.sog_kt,
                    "gps_cog_deg": sf.gps.cog_deg,
                    "gps_hdop": sf.gps.hdop,
                    "gps_fault": sf.gps.fault,
                    "wind_apparent_wind_speed_kt": sf.wind.apparent_wind_speed_kt,
                    "wind_apparent_wind_angle_deg": sf.wind.apparent_wind_angle_deg,
                    "wind_fault": sf.wind.fault,
                    "actuators_rudder_angle_deg": sf.actuators.rudder_angle_deg,
                    "actuators_mainsheet_pct": sf.actuators.mainsheet_pct,
                    "actuators_fault": sf.actuators.fault,
                }
            )

            # Decision row
            sel = dec.selected_response
            dec_rows.append(
                {
                    "sim_time_ms": dec.sim_time_ms,
                    "decision_id": dec.decision_id,
                    "sensor_frame_sequence": dec.sensor_frame_sequence,
                    "hazard_id": dec.risk_assessment.hazard_id,
                    "risk_score": dec.risk_assessment.risk_score,
                    "confidence": dec.risk_assessment.confidence,
                    "evidence_ids": list(dec.risk_assessment.evidence_ids),
                    "num_candidates": len(dec.candidates),
                    "selected_response_id": sel.response_id if sel else None,
                    "selected_action_type": sel.action_type if sel else None,
                    "selected_rudder_command_deg": sel.rudder_command_deg if sel else None,
                    "selected_sail_command_pct": sel.sail_command_pct if sel else None,
                    "selected_priority_score": sel.priority_score if sel else None,
                    "conflict_resolution_note": dec.conflict_resolution_note,
                }
            )

        df_gt = pl.DataFrame(gt_rows, schema=GROUND_TRUTH_SCHEMA)
        df_sf = pl.DataFrame(sf_rows, schema=SENSOR_SCHEMA)
        df_dec = pl.DataFrame(dec_rows, schema=DECISIONS_SCHEMA)

        return df_gt, df_sf, df_dec

    def to_jsonl(self, path: str | Path) -> None:
        """Export all recorded ticks as newline-delimited JSON (JSON Lines).

        Args:
            path: Target file path to write to.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            for rec in self._records:
                line_data = {
                    "ground_truth": rec.gt.model_dump(mode="json"),
                    "sensor_frame": rec.sf.model_dump(mode="json"),
                    "decision": rec.decision.model_dump(mode="json"),
                }
                f.write(json.dumps(line_data) + "\n")

    def export_parquet(self, output_dir: str | Path, prefix: str = "run") -> dict[str, Path]:
        """Exports ground truth, sensor, and decision logs as compressed Parquet files.

        Args:
            output_dir: Destination directory.
            prefix: Filename prefix (e.g. 'run' or 'sim005').

        Returns:
            Dictionary mapping dataset name to written Path.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        df_gt, df_sf, df_dec = self.to_polars()

        gt_path = out / f"{prefix}_ground_truth.parquet"
        sf_path = out / f"{prefix}_sensors.parquet"
        dec_path = out / f"{prefix}_decisions.parquet"

        df_gt.write_parquet(gt_path, compression="zstd")
        df_sf.write_parquet(sf_path, compression="zstd")
        df_dec.write_parquet(dec_path, compression="zstd")

        return {
            "ground_truth": gt_path,
            "sensors": sf_path,
            "decisions": dec_path,
        }

    def export_summary_json(
        self,
        path: str | Path,
        evaluation: EvaluationResult,
        oracle: OracleResult,
    ) -> Path:
        """Exports a structured JSON summary of the run and evaluation.

        Args:
            path: Destination file path.
            evaluation: EvaluationResult.
            oracle: OracleResult.

        Returns:
            Written Path.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        summary_data = {
            "evaluation": evaluation.model_dump(mode="json"),
            "oracle": oracle.model_dump(mode="json"),
            "total_ticks": len(self._records),
        }
        target.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
        return target
