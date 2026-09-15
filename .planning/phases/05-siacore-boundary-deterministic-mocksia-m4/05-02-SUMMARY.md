---
phase: 05-siacore-boundary-deterministic-mocksia-m4
plan: 02
subsystem: sia
tags: [sia, mocksia, hazard_detection, risk_assessment, candidate_responses, determinism]

requires:
  - phase: 05-siacore-boundary-deterministic-mocksia-m4
    provides: "SIACore boundary protocol"
provides:
  - "MockSIA: deterministic rule-based SIA reasoning engine conforming to SIACore"
  - "Multi-layer pipeline (L0 integrity, L2 broach precursor detection, L3 risk, L4 response generation)"
affects:
  - "05-03-PLAN"
  - "Phase 6 (Evaluator)"
  - "Phase 7 (End-to-End Pipeline)"

actuals:
  tokens: 2500
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "MockSIA multi-layer decision architecture"
  patterns:
    - "Max-3 prioritized candidate response generation without actuator overrides"

key-files:
  created:
    - src/sia_sim/sia/mock_sia.py
    - tests/unit/test_mock_sia.py
  modified:
    - src/sia_sim/sia/__init__.py

key-decisions:
  - "Implement L0-L4 reasoning pipeline (integrity, hazard detection, risk assessment, candidate responses)"
  - "Generate up to 3 candidate responses on broach precursor with deterministic conflict resolution"

requirements-completed:
  - ADAPT-02

coverage:
  - id: D1
    description: "MockSIA hazard detection and candidate generation"
    requirement: "ADAPT-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_mock_sia.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "Deterministic repeatability and sensor integrity degradation"
    requirement: "ADAPT-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_mock_sia.py"
        status: pass
      human_judgment: false

duration: 4min
completed: 2026-09-15
status: complete
---

# Plan 05-02 Summary: Deterministic MockSIA Implementation & Response Generation

**Implemented rule-based `MockSIA` engine featuring L0-L4 multi-layer reasoning (sensor integrity, broach precursor detection, risk scoring, max-3 candidate generation).**

## Accomplishments

- Implemented `MockSIA` in `src/sia_sim/sia/mock_sia.py` adhering strictly to `SIACore`.
- Evaluates sensor confidence (L0), detects broach precursors (L2), assesses risk (L3), and generates prioritized candidate responses (L4: `BEAR_AWAY`, `EASE_SHEETS`, `ALERT_CREW`).
- Created unit test suite in `tests/unit/test_mock_sia.py` verifying nominal conditions, broach detection, sensor fault degradation, and determinism.
