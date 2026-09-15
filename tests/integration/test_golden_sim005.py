"""Golden Integration Suite for SIM-005 Broach Precursor (GOLD-01, GOLD-02, GOLD-03)."""

from __future__ import annotations

from sia_sim.contracts.scenario import Scenario
from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios import get_sim005_scenario


class TestGoldenSIM005:
    def test_golden_sim005_end_to_end_pass(self) -> None:
        """GOLD-01, GOLD-02, GOLD-03: Full execution of SIM-005 achieving PASS verdict."""
        scenario = get_sim005_scenario(seed=42)
        assert isinstance(scenario, Scenario)
        assert scenario.scenario_id == "SIM-005"
        assert scenario.duration_ms == 20000

        runner = SimulationRunner()
        result = runner.run(scenario, run_id="GOLDEN-SIM005-01")

        # 1. Evaluator verdict must be strictly PASS
        assert result.evaluation.verdict == "PASS"

        # 2. Timing and safety margins
        assert result.evaluation.detection_latency_ms is not None
        assert result.evaluation.detection_latency_ms <= 1500
        assert result.evaluation.safety_margin_pct >= 15.0

        # 3. Zero false positives or false negatives
        assert result.evaluation.false_positives == 0
        assert result.evaluation.false_negatives == 0

        # 4. Oracle physical criteria
        assert result.oracle_result.expected_action_type == "EASE_MAIN"
        assert result.oracle_result.safety_envelope_breached is False
        assert result.oracle_result.hazard_onset_ms is not None
        assert 10000 <= result.oracle_result.hazard_onset_ms <= 15000

    def test_golden_sim005_bit_for_bit_repeatability(self) -> None:
        """Determinism invariant: 3 independent executions with seed=42 yield bit-identical logs."""
        scenario = get_sim005_scenario(seed=42)
        runner = SimulationRunner()

        res1 = runner.run(scenario, run_id="REP-01")
        res2 = runner.run(scenario, run_id="REP-02")
        res3 = runner.run(scenario, run_id="REP-03")

        gt1, sf1, dec1 = res1.recorder.to_polars()
        gt2, sf2, dec2 = res2.recorder.to_polars()
        gt3, sf3, dec3 = res3.recorder.to_polars()

        # Bit-for-bit identity across ground truth
        assert gt1.equals(gt2)
        assert gt2.equals(gt3)

        # Bit-for-bit identity across sensor frames
        assert sf1.equals(sf2)
        assert sf2.equals(sf3)

        # Bit-for-bit identity across decision payloads
        assert dec1.equals(dec2)
        assert dec2.equals(dec3)

        # Evaluation metrics bit-identical
        assert res1.evaluation.verdict == res2.evaluation.verdict == res3.evaluation.verdict
        assert (
            res1.evaluation.detection_latency_ms
            == res2.evaluation.detection_latency_ms
            == res3.evaluation.detection_latency_ms
        )
        assert (
            res1.evaluation.safety_margin_pct
            == res2.evaluation.safety_margin_pct
            == res3.evaluation.safety_margin_pct
        )

    def test_golden_sim005_performance_benchmark(self) -> None:
        """Performance requirement: 20s scenario executes > 10x faster than real-time."""
        scenario = get_sim005_scenario(seed=42)
        runner = SimulationRunner()
        result = runner.run(scenario)

        # 20s (2000 ticks) should finish in well under 2.0s wall-clock
        assert result.elapsed_wall_time_s < 2.0
        assert result.sim_speed_ratio > 10.0

    def test_golden_sim005_telemetry_data_isolation(self) -> None:
        """INV-01, INV-02: Strict segregation between Ground Truth and Sensor telemetry."""
        scenario = get_sim005_scenario(seed=42)
        runner = SimulationRunner()
        result = runner.run(scenario)

        df_gt, df_sf, df_dec = result.recorder.to_polars()

        assert len(df_gt) == 2000
        assert len(df_sf) == 2000
        assert len(df_dec) == 2000

        # Ground truth columns prohibited in sensor DataFrame
        prohibited_gt_columns = {
            "x_m",
            "y_m",
            "sog_m_s",
            "cog_deg",
            "heading_deg",
            "true_wind_speed_m_s",
            "true_wind_angle_deg",
            "wave_height_m",
            "wave_period_s",
            "current_speed_m_s",
            "current_direction_deg",
        }
        for col in prohibited_gt_columns:
            assert col not in df_sf.columns, f"Prohibited ground-truth column {col} in df_sensor!"

        # Verify Polars null types for absent mainsheet sensor
        assert "actuators_mainsheet_pct" in df_sf.columns
        assert df_sf["actuators_mainsheet_pct"].null_count() == 2000
