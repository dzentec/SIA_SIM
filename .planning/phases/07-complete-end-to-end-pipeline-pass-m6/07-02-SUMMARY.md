---
phase: 07-complete-end-to-end-pipeline-pass-m6
plan: 02
subsystem: cli
tags: [cli, telemetry, parquet, jsonl, exporter, main]

requires:
  - phase: 07-complete-end-to-end-pipeline-pass-m6
    provides: "SimulationRunner and Scenario Catalog"
provides:
  - "CLI command interface: sia-sim / python -m sia_sim"
  - "High-performance Parquet & JSONL export in RunRecorder"
affects:
  - "07-03-PLAN"

actuals:
  tokens: 2100
  tasks: 3
  commits: 1

tech-stack:
  added:
    - "CLI command line interface with argparse and rich progress/verdict formatting"
    - "PyArrow/Polars-backed Parquet telemetry exporter"
  patterns:
    - "Standard CLI return code conventions (0 on PASS, 1 on FAIL/error)"

key-files:
  created:
    - src/sia_sim/cli.py
    - src/sia_sim/__main__.py
    - tests/unit/test_cli.py
  modified:
    - src/sia_sim/recorder/run_recorder.py
    - pyproject.toml

key-decisions:
  - "Expose sia-sim executable script with customizable scenario, seed, quiet, and export flags"
  - "Export telemetry into partitioned Parquet files (ground_truth, sensors, decisions) and summary JSON"

requirements-completed:
  - GOLD-02

coverage:
  - id: D1
    description: "CLI command invocation and output formatting"
    requirement: "GOLD-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_cli.py::TestCLI::test_cli_default_invocation_pass"
        status: pass
      human_judgment: false
  - id: D2
    description: "Parquet and JSONL telemetry export pipeline"
    requirement: "GOLD-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_cli.py::TestCLI::test_cli_parquet_and_jsonl_export"
        status: pass
      human_judgment: false

duration: 3min
completed: 2026-09-15
status: complete
---

# Plan 07-02 Summary: CLI Entrypoint & Telemetry Export Pipeline

**Implemented the `sia-sim` CLI and Parquet / JSONL telemetry export pipeline.**

## Accomplishments

- Extended `RunRecorder` in `src/sia_sim/recorder/run_recorder.py` with `export_parquet()` and `export_summary_json()`.
- Created CLI in `src/sia_sim/cli.py` and `src/sia_sim/__main__.py`, and registered `sia-sim` script in `pyproject.toml`.
- Implemented unit tests in `tests/unit/test_cli.py` verifying default PASS runs, quiet modes, Parquet datasets, JSONL logs, and error handling.
