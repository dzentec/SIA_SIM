"""Unit tests for sia-sim CLI entrypoint (GOLD-02)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest

from sia_sim.cli import main


class TestCLI:
    def test_cli_default_invocation_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["SIM-005", "--quiet"])
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "PASS: SIM-005" in captured.out

    def test_cli_benign_invocation_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["SIM-BENIGN"])
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "Verdict:   PASS" in captured.out

    def test_cli_parquet_and_jsonl_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            exit_code = main([
                "SIM-005",
                "--output-dir",
                str(out_path),
                "--export-parquet",
                "--export-jsonl",
            ])

            assert exit_code == 0

            # Verify files were generated
            gt_parquet = out_path / "sim-005_seed42_ground_truth.parquet"
            sf_parquet = out_path / "sim-005_seed42_sensors.parquet"
            dec_parquet = out_path / "sim-005_seed42_decisions.parquet"
            trace_jsonl = out_path / "sim-005_seed42_trace.jsonl"
            summary_json = out_path / "sim-005_seed42_summary.json"

            assert gt_parquet.exists()
            assert sf_parquet.exists()
            assert dec_parquet.exists()
            assert trace_jsonl.exists()
            assert summary_json.exists()

            # Verify Parquet content can be read by Polars
            df_gt = pl.read_parquet(gt_parquet)
            assert len(df_gt) == 2000
            assert "x_m" in df_gt.columns

            df_sf = pl.read_parquet(sf_parquet)
            assert len(df_sf) == 2000
            assert "imu_roll_deg" in df_sf.columns
            # Strict boundary: zero ground truth in sensor log
            assert "x_m" not in df_sf.columns

    def test_cli_nonexistent_scenario_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["NON_EXISTENT_SCENARIO_XYZ"])
        captured = capsys.readouterr()

        assert exit_code != 0
        assert "Error loading scenario" in captured.err
