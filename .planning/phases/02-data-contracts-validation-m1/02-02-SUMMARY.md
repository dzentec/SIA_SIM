---
phase: 02-data-contracts-validation-m1
plan: 02
subsystem: contracts
tags: [contracts, scenario, decision_payload, evaluation_result, pydantic]

requires:
  - phase: 02-data-contracts-validation-m1
    provides: "SensorFrame and GroundTruthFrame data contracts"
provides:
  - "Scenario, ScenarioEvent, and VesselConfig contract models"
  - "RiskAssessment, CandidateResponse, and DecisionPayload contract models"
  - "OracleResult and EvaluationResult contract models"
affects:
  - "02-03-PLAN"
  - "Phase 5 (MockSIA)"
  - "Phase 6 (Oracle & Evaluator)"
  - "Phase 7 (End-to-End Pipeline)"

actuals:
  tokens: 2400
  tasks: 3
  commits: 1

tech-stack:
  added:
    - "Pydantic v2 validation models for scenarios and SIA evaluation"
  patterns:
    - "Max-3 candidate responses constraint for SIA Core decision model"
    - "Frozen scenario schedule with sorted timed events"

key-files:
  created:
    - src/sia_sim/contracts/scenario.py
    - src/sia_sim/contracts/evaluation.py
    - tests/unit/test_contracts_scenario.py
    - tests/unit/test_contracts_evaluation.py
  modified:
    - src/sia_sim/contracts/__init__.py

key-decisions:
  - "Validate candidate response counts (0-3) strictly in DecisionPayload"
  - "Enforce tuple types for event schedules and active event collections to guarantee immutability"

requirements-completed:
  - CONT-03
  - CONT-04
  - CONT-05

coverage:
  - id: D1
    description: "Scenario and ScenarioEvent contract validation"
    requirement: "CONT-03"
    verification:
      - kind: unit
        ref: "tests/unit/test_contracts_scenario.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "DecisionPayload and candidate architecture validation"
    requirement: "CONT-04"
    verification:
      - kind: unit
        ref: "tests/unit/test_contracts_evaluation.py"
        status: pass
      human_judgment: false
  - id: D3
    description: "OracleResult and EvaluationResult contracts"
    requirement: "CONT-05"
    verification:
      - kind: unit
        ref: "tests/unit/test_contracts_evaluation.py"
        status: pass
      human_judgment: false

duration: 4min
completed: 2026-09-15
status: complete
---

# Plan 02-02 Summary: Scenario, DecisionPayload & EvaluationResult Contracts

**Implemented strict Pydantic v2 contracts for `Scenario`, `DecisionPayload` (0-3 candidate architecture), `OracleResult`, and `EvaluationResult`.**

## Accomplishments

- Implemented `Scenario`, `ScenarioEvent`, and `VesselConfig` in `src/sia_sim/contracts/scenario.py`.
- Implemented `RiskAssessment`, `CandidateResponse`, `DecisionPayload`, `OracleResult`, and `EvaluationResult` in `src/sia_sim/contracts/evaluation.py`.
- Updated package exports in `src/sia_sim/contracts/__init__.py`.
- Verified 9 unit tests in `tests/unit/test_contracts_scenario.py` and 12 unit tests in `tests/unit/test_contracts_evaluation.py`.
