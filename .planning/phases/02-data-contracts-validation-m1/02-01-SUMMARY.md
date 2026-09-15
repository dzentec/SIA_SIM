---
phase: 02-data-contracts-validation-m1
plan: 01
subsystem: contracts
tags: [contracts, pydantic, sensor_frame, ground_truth_frame, strict_typing]

requires:
  - phase: 01-project-skeleton-deterministic-harness-m0
    provides: "Base environment, pytest runner, pyproject.toml"
provides:
  - "SensorFrame: strict immutable Pydantic model for observable sensor channels"
  - "GroundTruthFrame: strict immutable model for true physical state"
affects:
  - "02-02-PLAN"
  - "02-03-PLAN"
  - "Phase 3 (World & Dynamics)"
  - "Phase 4 (Sensor Model)"
  - "Phase 5 (SIACore Boundary)"

actuals:
  tokens: 2200
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "Pydantic v2 data models with ConfigDict(frozen=True, strict=True)"
  patterns:
    - "Strict null semantics: None signals represent failure/absence and are never coerced to 0.0"

key-files:
  created:
    - src/sia_sim/contracts/__init__.py
    - src/sia_sim/contracts/data.py
    - tests/unit/test_contracts_data.py
  modified: []

key-decisions:
  - "Enforce strict typing and frozen immutability across all data contract models"
  - "Use Optional[float] for sensor telemetry with explicit None semantics"

requirements-completed:
  - CONT-01
  - CONT-02

coverage:
  - id: D1
    description: "SensorFrame model with explicit None preservation"
    requirement: "CONT-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_contracts_data.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "GroundTruthFrame model isolating physical state"
    requirement: "CONT-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_contracts_data.py"
        status: pass
      human_judgment: false

duration: 3min
completed: 2026-09-15
status: complete
---

# Plan 02-01 Summary: SensorFrame & GroundTruthFrame Contract Models

**Implemented strict, immutable Pydantic v2 models for `SensorFrame` and `GroundTruthFrame` with strict `None` semantics for missing/failed signals.**

## Accomplishments

- Created `src/sia_sim/contracts/__init__.py` and `src/sia_sim/contracts/data.py`.
- Implemented `IMUReading`, `GPSReading`, `WindReading`, `ActuatorState`, `SensorFrame`, `VesselState`, `EnvironmentState`, and `GroundTruthFrame`.
- Enforced `ConfigDict(frozen=True, strict=True)` across all models.
- Verified 25 unit tests in `tests/unit/test_contracts_data.py` asserting field validation and None preservation.
