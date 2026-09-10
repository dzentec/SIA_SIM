# Feature Research

**Domain:** Deterministic Maritime Autonomous Systems Simulation & Testbed  
**Researched:** 2026-09-10  
**Confidence:** HIGH  

## Feature Landscape

### Table Stakes (MVP Baseline)

Features required for the simulation testbed to fulfill its core mandate.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Strict Boundary Isolation** | SIA Core must only consume `SensorFrame`; no leakage of Ground Truth | MEDIUM | Protocol interfaces (`Protocol`) with runtime structural checks |
| **Deterministic 100 Hz Clock** | Reproducibility across identical seeds; discrete 10 ms ticks | LOW | Integer simulation time in milliseconds (`sim_time_ms`) |
| **Scenario Loading & Freezing** | Immutability of test scenarios during execution | LOW | Pydantic model with frozen/immutable attributes |
| **Rigid Vessel Dynamics** | Simplified deterministic physics for vessel response to wind/waves/controls | MEDIUM | 3-DOF / 4-DOF planar dynamics (surge, sway, yaw, roll) |
| **Realistic Sensor Model** | Noise, bias, drift, latency, dropouts, and intermittent failures | MEDIUM | Seeded PRNG per sensor channel; `NULL`/`UNKNOWN` handling |
| **Autonomous Oracle Evaluation** | Independent expected behavior validation without peering into SIA internals | MEDIUM | State-space and physics constraint checks |
| **Automated Evaluator & Metrics** | Objective PASS/FAIL verdict, detection latency, stability margin | LOW | Structured `EvaluationResult` output |
| **BROACH PRECURSOR Scenario (SIM-005)** | Proves end-to-end vertical slice from wind gusts to rudder response and recovery | HIGH | Target Golden Scenario for MVP verification |

### Differentiators (Post-MVP & Full Scope)

Features that provide enhanced verification capabilities once MVP is stable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **NMEA/IMU Replay Adapter** | Validates SIA Core on recorded sea trials using the identical SensorFrame pipeline | MEDIUM | Core-006 replay protocol |
| **Batch Regression Matrix** | Monte Carlo sweeps across environmental seeds, vessel payloads, sensor noise | MEDIUM | Polars/Parquet telemetry aggregation |
| **Multi-Candidate Evaluation** | Evaluates up to 3 SIA candidate responses and conflict resolution decisions | MEDIUM | Defined in HLD section 7 |
| **Interactive Headless CLI / Runner** | Ergonomic execution of single scenarios or batch suites with formatted progress | LOW | Rich / Click CLI interface |

### Anti-Features (Deliberately Avoided in MVP)

Features that appear attractive but introduce non-determinism or unnecessary complexity.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **3D Rendering / Unity / Unreal** | Visual appeal for presentations | Introduces GPU dependencies, non-determinism, and slow headless runs | Headless execution + 2D telemetry plots / logs |
| **Continuous CFD Simulation** | Perceived hydrodynamic fidelity | Computational cost prevents 100 Hz batch regressions (>10x real-time) | Analytical parametric marine dynamics equations |
| **Deep RL in Simulation Loop** | Autonomous adaptive behaviors | Non-reproducible, untraceable failure modes | Rule-based and deterministic state-space models |
| **Wall-clock Synchronous Ticking** | Real-time sensor emulation | Slows tests down to real-time (minutes instead of seconds per run) | Discrete step-based clock with explicit delta |

## Feature Dependencies

```
[Scenario Engine] 
       └──requires──> [Data Contracts (CORE-002)]
                           └──requires──> [Project Skeleton]

[World & Dynamics] 
       └──requires──> [Scenario Engine]
       └──requires──> [Deterministic Clock]

[Sensor Model] 
       └──requires──> [World & Dynamics]

[Mock SIA / Adapter] 
       └──requires──> [Sensor Model (SensorFrame)]

[Oracle & Evaluator] 
       └──requires──> [World Model (GroundTruth)]
       └──requires──> [Mock SIA (DecisionPayload)]

[SIM-005 Golden Test] 
       └──requires──> All components integrated end-to-end
```

### Dependency Notes

- **Sensor Model strictly depends on Ground Truth**, but outputs only `SensorFrame`.
- **Evaluator depends on both Oracle (Ground Truth branch) and SIA Output (SIA branch)**, acting as the sole convergence point for scoring.
