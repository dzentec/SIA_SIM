---
phase: 06-oracle-evaluator-m5
plan: 01
subsystem: evaluator
tags: [evaluator, oracle, ground_truth, safety_envelope, recovery, broach_hazard]

requires:
  - phase: 02-data-contracts-validation-m1
    provides: "GroundTruthFrame and OracleResult data contracts"
provides:
  - "SafetyOracle: independent ground-truth physical safety evaluator"
  - "OracleConfig: configurable hazard thresholds and response windows"
affects:
  - "06-02-PLAN"
  - "06-03-PLAN"
  - "Phase 7 (End-to-End Pipeline)"

actuals:
  tokens: 2200
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "SafetyOracle physical evaluation engine"
  patterns:
    - "Strict ground truth evaluation isolated from SIA decision streams (INV-03)"

key-files:
  created:
    - src/sia_sim/evaluator/oracle.py
    - src/sia_sim/evaluator/__init__.py
    - tests/unit/test_oracle.py
  modified: []

key-decisions:
  - "Evaluate safety envelope and hazard onset purely from physical ground truth state"
  - "Verify recovery over the tail window of scenario execution without inspecting actuator commands"

requirements-completed:
  - EVAL-01

coverage:
  - id: D1
    description: "SafetyOracle hazard onset, envelope breach, and recovery computation"
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_oracle.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "AST isolation ensuring zero SIA imports"
    requirement: "EVAL-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_oracle.py"
        status: pass
      human_judgment: false

duration: 3min
completed: 2026-09-15
status: complete
---

# Plan 06-01 Summary: Independent Physical Safety Oracle

**Implemented `SafetyOracle` for ground-truth safety envelope evaluation, hazard onset timing, and recovery verification adhering to INV-03.**

## Accomplishments

- Implemented `SafetyOracle` and `OracleConfig` in `src/sia_sim/evaluator/oracle.py`.
- Evaluates `GroundTruthFrame` sequences to identify `hazard_onset_ms`, `expected_action_type`, `safety_envelope_breached`, `recovery_achieved`, and `severity`.
- Implemented unit tests in `tests/unit/test_oracle.py` verifying nominal runs, broach precursors, knockdown envelope breaches, empty frames, and AST architectural isolation.
