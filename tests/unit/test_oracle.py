"""Unit tests for SafetyOracle (INV-03, EVAL-01)."""

from __future__ import annotations

import ast
from pathlib import Path

from sia_sim.contracts.data import EnvironmentState, GroundTruthFrame, VesselState
from sia_sim.evaluator.oracle import OracleConfig, SafetyOracle


def _make_gt_frame(
    time_ms: int,
    seq: int = 0,
    heel_deg: float = 10.0,
    yaw_rate_deg_s: float = 0.0,
) -> GroundTruthFrame:
    """Helper creating minimal synthetic GroundTruthFrame."""
    return GroundTruthFrame(
        sim_time_ms=time_ms,
        vessel=VesselState(
            x_m=0.0,
            y_m=0.0,
            heading_deg=180.0,
            sog_m_s=3.5,
            cog_deg=180.0,
            heel_deg=heel_deg,
            pitch_deg=1.0,
            roll_rate_deg_s=0.0,
            yaw_rate_deg_s=yaw_rate_deg_s,
            rudder_angle_deg=0.0,
        ),
        environment=EnvironmentState(
            true_wind_speed_m_s=10.0,
            true_wind_angle_deg=180.0,
            wave_height_m=1.0,
            wave_period_s=5.0,
            current_speed_m_s=0.0,
            current_direction_deg=0.0,
        ),
        active_event_ids=(),
        sequence_number=seq,
    )


class TestSafetyOracle:
    def test_nominal_flat_run(self) -> None:
        oracle = SafetyOracle()
        frames = [_make_gt_frame(t, seq=i, heel_deg=8.0, yaw_rate_deg_s=0.2) for i, t in enumerate(range(0, 5000, 10))]
        result = oracle.evaluate(frames, scenario_id="SIM-NOMINAL")

        assert result.scenario_id == "SIM-NOMINAL"
        assert result.hazard_onset_ms is None
        assert result.expected_action_type is None
        assert result.safety_envelope_breached is False
        assert result.recovery_achieved is True
        assert result.severity in ("NONE", "LOW")

    def test_broach_precursor_hazard_detection(self) -> None:
        oracle = SafetyOracle(OracleConfig(heel_hazard_deg=25.0))
        frames = []
        seq = 0
        # T=0..10s: nominal heel 15 deg
        for t in range(0, 10000, 10):
            frames.append(_make_gt_frame(t, seq=seq, heel_deg=15.0, yaw_rate_deg_s=0.5))
            seq += 1
        # T=10s..14s: heel escalates to 32 deg (breaching 25 deg at t ~= 12350)
        for t in range(10000, 14000, 10):
            frac = (t - 10000) / 4000.0
            heel = 15.0 + 17.0 * frac
            frames.append(_make_gt_frame(t, seq=seq, heel_deg=heel, yaw_rate_deg_s=2.5))
            seq += 1
        # T=14s..16s: recovery to 10 deg
        for t in range(14000, 16000, 10):
            frac = (t - 14000) / 2000.0
            heel = 32.0 - 22.0 * frac
            frames.append(_make_gt_frame(t, seq=seq, heel_deg=heel, yaw_rate_deg_s=0.2))
            seq += 1
        # T=16s..20s: steady sailing at 10 deg
        for t in range(16000, 20000, 10):
            frames.append(_make_gt_frame(t, seq=seq, heel_deg=10.0, yaw_rate_deg_s=0.1))
            seq += 1

        result = oracle.evaluate(frames, scenario_id="SIM-005")

        assert result.hazard_onset_ms is not None
        assert 12000 <= result.hazard_onset_ms <= 13000
        assert result.expected_action_type == "EASE_MAIN"
        assert result.safety_envelope_breached is False
        assert result.recovery_achieved is True
        assert result.severity in ("HIGH", "CRITICAL")

    def test_safety_envelope_knockdown_breach(self) -> None:
        oracle = SafetyOracle(OracleConfig(heel_critical_deg=45.0))
        frames = []
        for i, t in enumerate(range(0, 10000, 10)):
            heel = 10.0 + (40.0 * (t / 10000.0))  # Reaches 50 deg
            frames.append(_make_gt_frame(t, seq=i, heel_deg=heel, yaw_rate_deg_s=3.5))

        result = oracle.evaluate(frames, scenario_id="SIM-CAPSIZE")

        assert result.safety_envelope_breached is True
        assert result.recovery_achieved is False
        assert result.severity == "CRITICAL"

    def test_empty_frames_handling(self) -> None:
        oracle = SafetyOracle()
        result = oracle.evaluate([])
        assert result.hazard_onset_ms is None
        assert result.safety_envelope_breached is False
        assert result.recovery_achieved is True

    def test_ast_oracle_isolation(self) -> None:
        """INV-03: Ensure SafetyOracle has zero imports of SIA decisions or sensor frames."""
        oracle_file = Path(__file__).parents[2] / "src" / "sia_sim" / "evaluator" / "oracle.py"
        tree = ast.parse(oracle_file.read_text(encoding="utf-8"))

        prohibited = {"SensorFrame", "DecisionPayload", "MockSIA", "SIACore"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name not in prohibited, f"Prohibited import in Oracle: {alias.name}"
