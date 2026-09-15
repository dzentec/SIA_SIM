---
phase: 07-complete-end-to-end-pipeline-pass-m6
plan: 03
subsystem: integration
tags: [integration, golden_test, sim005, broach_precursor, determinism, performance, m6]

requires:
  - phase: 07-complete-end-to-end-pipeline-pass-m6
    provides: "SimulationRunner and CLI"
provides:
  - "Golden integration test suite for SIM-005 Broach Precursor"
  - "Bit-for-bit repeatability verification across independent runs"
  - "Performance benchmark asserting >10x real-time execution"
  - "Telemetry data boundary and isolation verification"
affects:
  - "Milestone M0-M6 Completion"

actuals:
  tokens: 2200
  tasks: 1
  commits: 1

tech-stack:
  added:
    - "Golden integration test suite in tests/integration/test_golden_sim005.py"
  patterns:
    - "Deterministic multi-run DataFrame equality comparison"
    - "Automated PASS/FAIL scoring across complete end-to-end pipeline"

key-files:
  created:
    - tests/integration/__init__.py
    - tests/integration/test_golden_sim005.py
  modified: []

key-decisions:
  - "Verify full vertical slice of SIM-005: World -> Dynamics -> Sensors -> SIA -> Oracle -> Evaluator -> PASS"
  - "Assert bit-for-bit repeatability across independent runs and sub-second CPU performance (>10x real-time)"

requirements-completed:
  - GOLD-01
  - GOLD-02
  - GOLD-03

coverage:
  - id: D1
    description: "Full end-to-end execution of SIM-005 achieving PASS verdict"
    requirement: "GOLD-01, GOLD-02, GOLD-03"
    verification:
      - kind: integration
        ref: "tests/integration/test_golden_sim005.py::TestGoldenSIM005::test_golden_sim005_end_to_end_pass"
        status: pass
      human_judgment: false
  - id: D2
    description: "Bit-for-bit repeatability across independent runs with identical seed"
    requirement: "GOLD-03"
    verification:
      - kind: integration
        ref: "tests/integration/test_golden_sim005.py::TestGoldenSIM005::test_golden_sim005_bit_for_bit_repeatability"
        status: pass
      human_judgment: false
  - id: D3
    description: "Performance benchmark (>10x real-time execution)"
    requirement: "GOLD-02"
    verification:
      - kind: integration
        ref: "tests/integration/test_golden_sim005.py::TestGoldenSIM005::test_golden_sim005_performance_benchmark"
        status: pass
      human_judgment: false
  - id: D4
    description: "Strict telemetry data isolation and null preservation"
    requirement: "GOLD-02"
    verification:
      - kind: integration
        ref: "tests/integration/test_golden_sim005.py::TestGoldenSIM005::test_golden_sim005_telemetry_data_isolation"
        status: pass
      human_judgment: false

duration: 4min
completed: 2026-09-15
status: complete
---

# Plan 07-03 Summary: Golden SIM-005 Integration Suite & Deterministic Repeatability

**Implemented the golden integration test suite asserting end-to-end PASS verification, determinism, and performance for SIM-005 Broach Precursor.**

## Accomplishments

- Created `tests/integration/test_golden_sim005.py` and `tests/integration/__init__.py`.
- **Test 1 (End-to-End PASS):** Validated full simulation pipeline from physics through MockSIA to Oracle and Evaluator on canonical SIM-005, confirming:
  - `verdict == "PASS"`
  - `detection_latency_ms <= 1500`
  - `safety_margin_pct >= 15.0%`
  - `false_positives == 0` and `false_negatives == 0`
  - `expected_action_type == "EASE_MAIN"`
- **Test 2 (Bit-for-bit Repeatability):** Proved 3 independent runs with seed=42 yield identical Polars DataFrames across Ground Truth, SensorFrame, and DecisionPayload.
- **Test 3 (Performance Benchmark):** Proved 20s (2000 tick) simulation executes in $< 2.0$s on CPU ($> 10\times$ faster than real-time).
- **Test 4 (Data Boundary Isolation):** Proved `df_sensor` contains zero ground-truth columns and preserves explicit nulls.
