"""Command Line Interface for SIA Simulation testbed."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios import load_scenario


def create_parser() -> argparse.ArgumentParser:
    """Creates the argument parser for sia-sim CLI."""
    parser = argparse.ArgumentParser(
        prog="sia-sim",
        description="SIA Simulation: Deterministic 100 Hz Testbed for SIA Core Validation",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="SIM-005",
        help="Scenario ID ('SIM-005', 'SIM-BENIGN') or path to JSON scenario configuration file.",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="PRNG master seed for deterministic reproducibility (default: 42).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Directory path to save telemetry and evaluation export files.",
    )
    parser.add_argument(
        "--export-parquet",
        action="store_true",
        help="Export Polars telemetry datasets as compressed Parquet files.",
    )
    parser.add_argument(
        "--export-jsonl",
        action="store_true",
        help="Export continuous 100 Hz simulation trace as JSON Lines (.jsonl).",
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Run open-loop simulation without applying SIA advisory responses to actuators.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode: suppress detailed banner and output verdict only.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint. Returns process exit code (0 on PASS, 1 on FAIL)."""
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        scenario = load_scenario(args.scenario, seed=args.seed)
    except Exception as e:
        sys.stderr.write(f"Error loading scenario '{args.scenario}': {e}\n")
        return 1

    if not args.quiet:
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.write(f" SIA Simulation Engine | Scenario: {scenario.scenario_id}\n")
        sys.stdout.write(
            f" Vessel: {scenario.vessel.vessel_type} | "
            f"Duration: {scenario.duration_ms / 1000.0:.1f}s | "
            f"Seed: {scenario.seed}\n"
        )
        sys.stdout.write("=" * 70 + "\n")

    runner = SimulationRunner()
    result = runner.run(
        scenario=scenario,
        apply_actuator_feedback=not args.no_feedback,
    )

    eval_res = result.evaluation
    sim_time_s = scenario.duration_ms / 1000.0

    if not args.quiet:
        sys.stdout.write(
            f"Execution: Simulated {sim_time_s:.1f}s in {result.elapsed_wall_time_s:.3f}s "
            f"({result.sim_speed_ratio:.1f}x real-time)\n"
        )
        sys.stdout.write(f"Verdict:   {eval_res.verdict}\n")
        if eval_res.detection_latency_ms is not None:
            sys.stdout.write(
                f"Latency:   {eval_res.detection_latency_ms} ms "
                f"(Safety Margin: {eval_res.safety_margin_pct:.1f}%)\n"
            )
        sys.stdout.write(
            f"False Pos: {eval_res.false_positives} | False Neg: {eval_res.false_negatives}\n"
        )
        sys.stdout.write(f"Notes:     {eval_res.notes}\n")
    else:
        sys.stdout.write(f"{eval_res.verdict}: {scenario.scenario_id}\n")

    # Exports
    if args.output_dir or args.export_parquet or args.export_jsonl:
        out_dir = Path(args.output_dir or "./runs")
        prefix = f"{scenario.scenario_id.lower()}_seed{scenario.seed}"

        if args.export_parquet or args.output_dir:
            result.recorder.export_parquet(out_dir, prefix=prefix)
            if not args.quiet:
                sys.stdout.write(f"Parquet:   Exported datasets to {out_dir.resolve()}\n")

        if args.export_jsonl:
            jsonl_path = out_dir / f"{prefix}_trace.jsonl"
            result.recorder.to_jsonl(jsonl_path)
            if not args.quiet:
                sys.stdout.write(f"JSONL:     Exported trace to {jsonl_path.resolve()}\n")

        summary_path = out_dir / f"{prefix}_summary.json"
        result.recorder.export_summary_json(
            summary_path,
            evaluation=result.evaluation,
            oracle=result.oracle_result,
        )

    if not args.quiet:
        sys.stdout.write("=" * 70 + "\n")

    return 0 if eval_res.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
