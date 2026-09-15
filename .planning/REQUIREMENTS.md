# Requirements: SIA Simulation

**Defined:** 2026-09-10  
**Core Value:** Strictly maintain the system boundary where only `SensorFrame` enters SIA Core, ensuring deterministic end-to-end execution of the Broach Precursor scenario (SIM-005) with automated Oracle evaluation and reproducible PASS/FAIL verification without simulation ever making decisions on behalf of SIA.

## v1 Requirements

Requirements for MVP Milestone (M0–M6: First Golden Test BROACH PRECURSOR).

### Project Skeleton & Tooling (M0)

- [ ] **SKEL-01**: User/developer can install and run the project using `uv` with Python 3.12+, `pyproject.toml`, and strict linting/typing configs.
- [ ] **SKEL-02**: Simulation executes against a deterministic discrete integer clock (`SimulationClock`) running at 100 Hz (10 ms step) with advance and reset capabilities.
- [ ] **SKEL-03**: Simulation generates reproducible runs using explicit, isolated PRNG generators per seed without global random state contamination.

### Data Contracts (M1)

- [ ] **CONT-01**: System validates `SensorFrame` data structure containing timestamps, IMU, GPS, wind, and actuator telemetry per CORE-002/003.
- [ ] **CONT-02**: System validates `GroundTruthFrame` and `WorldState` models representing true physical state.
- [ ] **CONT-03**: System loads, validates, and freezes immutable `Scenario` configurations and timed event schedules per CORE-004.
- [ ] **CONT-04**: System validates `DecisionPayload` containing candidate responses (up to 3), selected response, and decision trace.
- [ ] **CONT-05**: System validates `OracleResult` and `EvaluationResult` contracts per CORE-005.

### World & Vessel Dynamics (M2)

- [ ] **PHYS-01**: World model computes environmental ground truth (mean wind, gust profiles, sea state, current) at 100 Hz.
- [ ] **PHYS-02**: Vessel dynamics calculates rigid-body planar dynamics (surge, sway, yaw, roll) driven by environmental forces and control inputs.
- [ ] **PHYS-03**: Numerical integration advances physical state using fixed-step deterministic methods.

### Sensor Model (M3)

- [ ] **SENS-01**: Sensor model transforms `GroundTruthFrame` into observable `SensorFrame` across all defined channels.
- [ ] **SENS-02**: Sensor pipeline applies configurable Gaussian noise, static bias, and gradual drift.
- [ ] **SENS-03**: Sensor pipeline injects latency, dropouts, and frozen values while preserving explicit `None`/`UNKNOWN` markers without zero-coercion.

### SIA Core Adapter (M4)

- [ ] **ADAPT-01**: Hard boundary protocol (`SIACore`) enforces that only `SensorFrame` can be received and processed.
- [ ] **ADAPT-02**: `MockSIA` implementation generates predictable candidate responses, risk scores, and actuator commands for scenario testing.

### Oracle & Evaluator (M5)

- [ ] **EVAL-01**: Independent physical Oracle evaluates ground truth dynamics to determine hazard onset, required intervention window, and recovery conditions.
- [ ] **EVAL-02**: Evaluator compares SIA decision stream with Oracle expectations to compute detection latency, false positives/negatives, and safety margins.
- [ ] **EVAL-03**: Evaluator produces structured `EvaluationResult` with deterministic PASS/FAIL verdict.

### Golden Test: SIM-005 Broach Precursor (M6)

- [ ] **GOLD-01**: System loads and validates the SIM-005 Broach Precursor scenario specification.
- [ ] **GOLD-02**: End-to-end simulation runner executes SIM-005 through World -> Dynamics -> Sensors -> SIA -> Oracle -> Evaluator loop.
### Workbench UI & Interactive Studio (Phase 8)

- [ ] **WB-01**: SIA Core Advisory Panel displays active nominal monitoring status and transitions into high-contrast primary and candidate recommendations upon hazard onset.
- [ ] **WB-02**: Multi-track timeline supports interactive event creation (Wind Gust, Wave Impact/Slam, Sensor Faults) via toolbar or track clicks.
- [ ] **WB-03**: Timeline event markers are draggable along time tracks and editable/deletable via event inspector.
- [ ] **WB-04**: Timeline supports zoom (1x to 10x), horizontal pan/scroll, and adaptive multi-scale time grid.
- [ ] **WB-05**: User can configure simulation duration (`DURATION: [ 20 ] s`) with automated re-simulation.
- [ ] **WB-06**: Marine Console displays dedicated Pitch Inclinometer (килевая качка) and Heave/Vertical Acceleration meter (вертикальная качка).
- [ ] **WB-07**: Marine Console displays dedicated Slamming/Hull Shock instrument (слеминг) with peak impact force (kN) and shock pulse alert.

## v2 Requirements

Deferred to post-MVP milestones.

### Test Suite Expansion (M7)

- **SUITE-01**: Comprehensive execution of remaining standard scenarios (SIM-001 through SIM-007).
- **SUITE-02**: Property-based fuzz testing of sensor fault matrices using Hypothesis.

### Replay System (M8)

- **REPLAY-01**: Ingestion of real-world NMEA 0183/2000 and binary IMU logs.
- **REPLAY-02**: Replay adapter mapping recorded maritime telemetry into standard `SensorFrame` streams.

### Batch & Regression Suite (M9)

- **BATCH-01**: High-throughput parallel execution across seed matrices and parameter variations.
- **BATCH-02**: Polars-backed summary dashboards, Parquet trace exports, and regression delta reporting.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud / Distributed Runner | Local laboratory testbed is the primary goal; distributed execution adds network overhead and deployment complexity. |
| Full 3D CFD Hydrodynamics | Engineering planar equations provide sufficient fidelity at 100 Hz for algorithmic safety validation without CFD compute costs. |
| Production SIA Core Implementation | Simulation provides the evaluation harness and MockSIA; the production SIA decision engine is developed in a separate repository. |
| Graphical 3D Visualizer / GUI | Headless operation with structured data outputs (Parquet, logs, CLI) ensures fast test runs and CI/CD compatibility. |
| Wall-Clock Synchronous Delays | Non-deterministic and slow; simulation time must advance strictly via integer tick increments. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SKEL-01 | Phase 1 | Pending |
| SKEL-02 | Phase 1 | Pending |
| SKEL-03 | Phase 1 | Pending |
| CONT-01 | Phase 2 | Pending |
| CONT-02 | Phase 2 | Pending |
| CONT-03 | Phase 2 | Pending |
| CONT-04 | Phase 2 | Pending |
| CONT-05 | Phase 2 | Pending |
| PHYS-01 | Phase 3 | Pending |
| PHYS-02 | Phase 3 | Pending |
| PHYS-03 | Phase 3 | Pending |
| SENS-01 | Phase 4 | Pending |
| SENS-02 | Phase 4 | Pending |
| SENS-03 | Phase 4 | Pending |
| ADAPT-01 | Phase 5 | Pending |
| ADAPT-02 | Phase 5 | Pending |
| EVAL-01 | Phase 6 | Pending |
| EVAL-02 | Phase 6 | Pending |
| EVAL-03 | Phase 6 | Pending |
| GOLD-01 | Phase 7 | Pending |
| GOLD-02 | Phase 7 | Pending |
| GOLD-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-09-10*
*Last updated: 2026-09-10 after initialization*
