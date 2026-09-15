---
phase: 05-siacore-boundary-deterministic-mocksia-m4
plan: 01
subsystem: sia
tags: [sia, boundary, protocol, ast, isolation, architecture]

requires:
  - phase: 02-data-contracts-validation-m1
    provides: "SensorFrame and DecisionPayload data contracts"
provides:
  - "SIACore Protocol definition enforcing process(frame: SensorFrame) -> DecisionPayload"
  - "Automated AST inspection tests guaranteeing zero Ground Truth or Physics imports in SIA package"
affects:
  - "05-02-PLAN"
  - "05-03-PLAN"
  - "Phase 7 (End-to-End Pipeline)"

actuals:
  tokens: 2200
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "SIACore Protocol and static AST isolation tests"
  patterns:
    - "Hard system boundary isolation (INV-01, INV-02)"

key-files:
  created:
    - src/sia_sim/sia/protocol.py
    - src/sia_sim/sia/__init__.py
    - tests/unit/test_sia_boundary.py
  modified: []

key-decisions:
  - "Prohibit any import or reference to GroundTruthFrame or physics engines inside sia package via automated AST tests"
  - "Require SIACore protocol implementers to provide process and reset methods"

requirements-completed:
  - ADAPT-01

coverage:
  - id: D1
    description: "SIACore protocol definition and runtime checks"
    requirement: "ADAPT-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_sia_boundary.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "AST boundary enforcement"
    requirement: "ADAPT-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_sia_boundary.py"
        status: pass
      human_judgment: false

duration: 3min
completed: 2026-09-15
status: complete
---

# Plan 05-01 Summary: SIACore Boundary Protocol & AST Isolation Enforcement

**Defined `SIACore` runtime protocol and implemented automated AST boundary testing preventing any ground-truth leakage into SIA algorithms.**

## Accomplishments

- Implemented `SIACore` protocol in `src/sia_sim/sia/protocol.py` strictly requiring `process(frame: SensorFrame) -> DecisionPayload`.
- Created AST boundary test suite in `tests/unit/test_sia_boundary.py` scanning the AST of all modules in `src/sia_sim/sia/` to prevent imports of `GroundTruthFrame`, `VesselDynamics`, or physics internals.
- Verified protocol compliance and runtime input validation.
