# SIA Simulation

## What This Is

SIA Simulation is a deterministic, local physics- and sensor-driven simulation testbed for validating the Safety & Intelligence Architecture (SIA) Core. It generates synthetic vessel dynamics, environmental conditions, and sensor observations (SensorFrame) at 100 Hz, feeding them to SIA Core while independently verifying SIA responses against Ground Truth and physical safety constraints using an Oracle and Evaluator.

## Core Value

The single most critical requirement: strictly maintain the system boundary where only `SensorFrame` enters SIA Core, ensuring deterministic end-to-end execution of the Broach Precursor scenario (SIM-005) with automated Oracle evaluation and reproducible PASS/FAIL verification without simulation ever making decisions on behalf of SIA.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **M0: Project Skeleton** — Setup clean Python 3.12+ repository with `uv`, package configuration (`pyproject.toml`), deterministic test harness (`pytest`), and runner structure.
- [ ] **M1: Data Contracts** — Implement Pydantic / typed contracts: `SensorFrame`, `GroundTruthFrame`, `Scenario`, `OracleResult`, `EvaluationResult`, `DecisionPayload` matching CORE-002..006 specifications.
- [ ] **M2: World & Vessel Dynamics** — Deterministic 100 Hz simulation clock, world state (wind, waves, current), and engineering vessel dynamics model.
- [ ] **M3: Sensor Model** — Transform ground truth into observable `SensorFrame` with contract-defined noise, bias, drift, latency, dropouts, and failure modes.
- [ ] **M4: SIA Core Adapter** — Clean boundary adapter and `MockSIA` implementing candidate response generation and decision lifecycle.
- [ ] **M5: Oracle & Evaluator** — Independent physical oracle rules and evaluator computing detection latency, response correctness, and safety margin.
- [ ] **M6: First Golden Test (SIM-005)** — End-to-end execution of the Broach Precursor scenario with automated evaluation and verified PASS verdict.

### Out of Scope

- **Cloud / Distributed Execution** — MVP is strictly a local workstation testbed.
- **CFD / High-Fidelity Hydrodynamics** — Replaced by deterministic engineering physics models.
- **Full SIA Production Engine** — Simulation uses `MockSIA` with interchangeable protocol; SIA core production logic is developed separately.
- **GUI / Visualizer Frontend** — MVP operates headless with CLI, structured logs, and data exports.
- **Reinforcement Learning / LLM Agents** — No non-deterministic agents in the simulation loop.
- **Full Replay & Batch Regressions (M7-M9)** — Deferred to Milestone 2 after Golden Test M6 succeeds.

## Context

- Translated from architecture specifications: `CORE-001` through `CORE-007` and `SIA-SIM-HLD-001`.
- Follows the Implementation Plan baseline `SIA-SIM-MVP-001`.
- Built to provide regression safety and repeatable laboratory testing for maritime autonomous navigation.

## Constraints

- **Tech Stack**: Python 3.12+, `uv` package manager, Pydantic, NumPy/SciPy, Polars/PyArrow, pytest.
- **Architecture Boundary**: Hard boundary — SIA Core must never access `GroundTruthFrame`, `WorldState`, Dynamics state, or Oracle internals.
- **Determinism**: Fully deterministic execution driven by discrete simulation clock (10 ms / 100 Hz tick) and explicit PRNG seeds; zero reliance on wall-clock time.
- **Performance**: Capable of running faster than real-time for batch test execution.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scope MVP to M0–M6 | Establishes the complete vertical proof of concept (SIM-005 Golden Test) before expanding into broader regression suites | — Pending |
| Use `uv` for Python tooling | Provides fast, reproducible dependency resolution and virtual environments | — Pending |
| Protocol-based SIA Core boundary | Enables drop-in replacement of MockSIA with real SIA Core without simulator code modifications | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-10 after initialization*
