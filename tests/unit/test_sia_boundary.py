"""Architectural boundary AST inspection and protocol conformance tests."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from sia_sim.contracts.data import (
    ActuatorState,
    GPSReading,
    IMUReading,
    SensorFrame,
    WindReading,
)
from sia_sim.contracts.evaluation import DecisionPayload, RiskAssessment
from sia_sim.sia.protocol import SIACore

FORBIDDEN_MODULES = {
    "sia_sim.physics",
    "sia_sim.physics.dynamics",
    "sia_sim.physics.environment",
    "sia_sim.physics.forces",
    "sia_sim.physics.integrator",
    "sia_sim.physics.world",
}

FORBIDDEN_SYMBOLS = {
    "GroundTruthFrame",
    "VesselState",
    "EnvironmentState",
    "WorldModel",
    "VesselDynamics",
    "WindModel",
    "WaveModel",
    "CurrentModel",
}


def make_dummy_sensor_frame(t_ms: int = 0) -> SensorFrame:
    return SensorFrame(
        sim_time_ms=t_ms,
        imu=IMUReading(
            roll_deg=0.0,
            pitch_deg=0.0,
            roll_rate_deg_s=0.0,
            pitch_rate_deg_s=0.0,
            yaw_rate_deg_s=0.0,
            accel_x_m_s2=0.0,
            accel_y_m_s2=0.0,
            accel_z_m_s2=9.81,
            fault=False,
        ),
        gps=GPSReading(
            latitude_deg=43.5,
            longitude_deg=16.4,
            sog_kt=5.0,
            cog_deg=45.0,
            hdop=1.0,
            fault=False,
        ),
        wind=WindReading(
            apparent_wind_speed_kt=15.0,
            apparent_wind_angle_deg=45.0,
            fault=False,
        ),
        actuators=ActuatorState(
            rudder_angle_deg=0.0,
            mainsheet_pct=None,
            fault=False,
        ),
        sequence_number=0,
    )


class DummyCompliantSIA:
    """Minimal compliant implementation of SIACore."""

    def process(self, frame: SensorFrame) -> DecisionPayload:
        if not isinstance(frame, SensorFrame):
            raise TypeError(f"Expected SensorFrame, got {type(frame)}")
        return DecisionPayload(
            decision_id=f"DEC-{frame.sim_time_ms}",
            sim_time_ms=frame.sim_time_ms,
            sensor_frame_sequence=frame.sequence_number,
            risk_assessment=RiskAssessment(
                hazard_id=None,
                risk_score=0.0,
                confidence=1.0,
                evidence_ids=(),
            ),
            candidates=(),
            selected_response=None,
            conflict_resolution_note="Nominal conditions, no response required",
        )

    def reset(self) -> None:
        pass


class TestSIABoundaryProtocol:
    def test_protocol_runtime_check(self) -> None:
        engine = DummyCompliantSIA()
        assert isinstance(engine, SIACore)

    def test_protocol_rejects_non_compliant_class(self) -> None:
        class IncompleteSIA:
            def process(self, frame: Any) -> Any:
                return None

        assert not isinstance(IncompleteSIA(), SIACore)

    def test_strict_ast_inspection_of_sia_package(self) -> None:
        """Inspects AST of all python files in src/sia_sim/sia/ ensuring NO ground-truth leakage."""
        sia_dir = Path(__file__).resolve().parent.parent.parent / "src" / "sia_sim" / "sia"
        assert sia_dir.exists() and sia_dir.is_dir()

        py_files = list(sia_dir.glob("*.py"))
        assert len(py_files) > 0, "No python files found in src/sia_sim/sia/"

        for py_file in py_files:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                # 1. Check 'import x'
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in FORBIDDEN_MODULES, (
                            f"Illegal module import '{alias.name}' found in {py_file.name}"
                        )
                # 2. Check 'from x import y'
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert mod not in FORBIDDEN_MODULES, f"Illegal module import from '{mod}' found in {py_file.name}"
                    for alias in node.names:
                        assert alias.name not in FORBIDDEN_SYMBOLS, (
                            f"Illegal symbol import '{alias.name}' from '{mod}' found in {py_file.name}"
                        )

    def test_process_enforces_sensor_frame_type(self) -> None:
        engine = DummyCompliantSIA()
        valid_frame = make_dummy_sensor_frame(0)

        payload = engine.process(valid_frame)
        assert isinstance(payload, DecisionPayload)
        assert payload.sim_time_ms == 0

        # Passing non-SensorFrame must raise TypeError
        with pytest.raises(TypeError, match="Expected SensorFrame"):
            engine.process({"dummy": "dict"})  # type: ignore[arg-type]
