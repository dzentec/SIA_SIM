# Project Research Summary

**Project:** SIA Simulation  
**Domain:** Deterministic Maritime Autonomous Systems Simulation & Testbed  
**Researched:** 2026-09-10  
**Confidence:** HIGH  

## Executive Summary

SIA Simulation is designed as a standalone, deterministic 100 Hz simulation testbed built to evaluate the Safety & Intelligence Architecture (SIA) Core. Research confirms that the architectural separation between Ground Truth (owned by WorldModel/Dynamics/Oracle) and Observable State (packaged as `SensorFrame` for SIA Core) is the foundational requirement for building a trustworthy, leak-free evaluation environment.

The recommended engineering approach leverages Python 3.12+ with `uv`, `pydantic` (v2) for strict contracts, `numpy`/`scipy` for fixed-step deterministic physics, and `polars`/`pyarrow` for high-throughput telemetry storage. The simulation loop operates entirely on integer discrete time ticks (10 ms / 100 Hz), avoiding any reliance on wall-clock time or non-deterministic asynchronous event loops.

Key risks identified include information leakage across the SIA boundary, silent non-determinism from unseeded PRNGs, and semantic corruption of missing sensor signals (coercing `NULL`/`UNKNOWN` to `0.0`). The planned phase structure (M0–M6) directly mitigates these hazards through architectural type safety, isolated PRNG instances, and explicit sensor fault modeling.

## Key Findings

### Recommended Stack

- **Python 3.12+ & uv**: Fast, reproducible project management with strict typing.
- **Pydantic v2**: High-speed validation of contracts (`SensorFrame`, `GroundTruthFrame`, `Scenario`).
- **NumPy & SciPy**: Vectorized rigid-body planar dynamics with deterministic numerical integration.
- **Polars & PyArrow**: Zero-copy Parquet telemetry export and regression metrics calculation.
- **pytest & hypothesis**: Fast unit testing and property-based fuzzing of sensor fault modes.

### Expected Features

**Must have (MVP Baseline — M0..M6):**
- Strict architectural boundary: only `SensorFrame` enters SIA Core.
- Deterministic 100 Hz clock with integer tick progression.
- Scenario loading, validation, and immutability freezing.
- Deterministic 3/4-DOF planar vessel dynamics.
- Realistic sensor degradation (noise, bias, latency, dropouts, fault flags).
- Independent Oracle evaluating physical constraints from Ground Truth.
- Objective Evaluator generating PASS/FAIL verdicts.
- End-to-end execution of the SIM-005 Broach Precursor Golden Test.

**Defer (v2+ / M7..M9):**
- Full test suite expansion across all scenarios (M7).
- NMEA/IMU Replay Adapter (M8).
- Batch Monte Carlo regression runner (M9).
- Advanced hydrodynamics or CFD integration.

### Architecture Approach

The architecture enforces a strict unidirectional pipeline:
`Scenario -> WorldModel -> VesselDynamics -> SensorModel -> SensorFrame -> SIA Core -> DecisionPayload -> RunRecorder`.
In parallel, an independent verification branch evaluates:
`GroundTruth -> Oracle -> Evaluator <- DecisionPayload`.

### Critical Pitfalls

1. **Information Leakage**: Prevented by strict Protocol interfaces, immutable data objects, and AST import boundaries.
2. **Hidden Non-Determinism**: Prevented by passing explicit `Generator` instances and driving all state transitions through `SimulationClock.time_ms`.
3. **NULL/UNKNOWN to Zero Coercion**: Prevented by `Optional` types, strict null handling, and explicit status enums.
4. **ODE Solver Drag**: Prevented by fixed-step 10 ms integration tuned for faster-than-real-time execution.

## Roadmap Implications

The research directly validates the 7-phase MVP roadmap (M0 to M6):
- **Phase 1 (Skeleton)**: Tooling, `uv`, pyproject.toml, clock, test runner.
- **Phase 2 (Contracts)**: Pydantic schemas for all core frames and protocols.
- **Phase 3 (World & Dynamics)**: 100 Hz physics engine, environmental forces, planar dynamics.
- **Phase 4 (Sensor Model)**: Degradation pipeline and failure injection.
- **Phase 5 (SIA Core Adapter)**: Boundary isolation protocol and MockSIA implementation.
- **Phase 6 (Oracle & Evaluator)**: Truth-based safety oracle and verdict calculator.
- **Phase 7 (SIM-005 Golden Test)**: Integration of the Broach Precursor scenario with end-to-end PASS assertion.
