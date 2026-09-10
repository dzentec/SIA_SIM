# Architecture Research

**Domain:** Deterministic Maritime Autonomous Systems Simulation & Testbed  
**Researched:** 2026-09-10  
**Confidence:** HIGH  

## Standard Architecture

### System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             SCENARIO LAYER                                  │
│  ┌───────────────────────┐                     ┌─────────────────────────┐  │
│  │    Scenario Engine    │────────────────────→│     Simulation Clock    │  │
│  │ (Loads & Freezes Spec)│                     │   (Deterministic 10ms)  │  │
│  └───────────┬───────────┘                     └────────────┬────────────┘  │
└──────────────┼──────────────────────────────────────────────┼───────────────┘
               │                                              │
               ▼                                              ▼
┌──────────────────────────────────────────────┐ ┌────────────────────────────┐
│              PHYSICS & ENVIRONMENT           │ │     EVALUATION BRANCH      │
│  ┌────────────────────────────────────────┐  │ │                            │
│  │ World Model (Wind, Waves, Currents)    │  │ │ ┌────────────────────────┐ │
│  └───────────────────┬────────────────────┘  │ │ │  Independent Oracle    │ │
│                      ▼                       │ │ │ (Physical Constraints) │ │
│  ┌────────────────────────────────────────┐  │ │ └───────────┬────────────┘ │
│  │ Vessel Dynamics (Planar 3/4-DOF)       │  │ │             │              │
│  └───────────────────┬────────────────────┘  │ │             ▼              │
│                      ▼                       │ │ ┌────────────────────────┐ │
│         [GroundTruthFrame output]            │─┼─│       Evaluator        │ │
│                      │                       │ │ │ (Latency, FP/FN, PASS) │ │
│                      ▼                       │ │ └───────────▲────────────┘ │
│  ┌────────────────────────────────────────┐  │ │             │              │
│  │ Sensor Model (Noise, Bias, Dropouts)   │  │ │             │              │
│  └───────────────────┬────────────────────┘  │ │             │              │
└──────────────────────┼───────────────────────┘ └─────────────┼──────────────┘
                       │                                       │
            ═══════════╪═══════════════════════════════════════╪═══════════════
                       │ HARD ARCHITECTURAL BOUNDARY:          │
                       │ ONLY SensorFrame CROSSES              │
                       ▼                                       │
┌──────────────────────────────────────────────────────────────┼──────────────┐
│                      SIA CORE LAYER                          │              │
│  ┌─────────────────────────────────────────────────────────┐ │              │
│  │ SIA Core / MockSIA                                      │ │              │
│  │ (Risk Assessment -> Candidate Responses -> Resolution)  │─┘              │
│  └─────────────────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **ScenarioEngine** | Parses scenario YAML/JSON, validates constraints, freezes state | Pydantic model parser + immutable scenario wrapper |
| **SimulationClock** | Maintains integer step `time_ms` (100 Hz / 10 ms), provides advance/reset | Discrete integer counter |
| **WorldModel** | Calculates dynamic environmental forces (gusts, sea state) | Vectorized NumPy math with PRNG seed |
| **VesselDynamics** | Updates vessel surge, sway, yaw rate, roll angle, and positions | Euler/RK4 numerical integration of equations of motion |
| **SensorModel** | Injects realistic degradation (noise, bias, latency queue, dropouts) | Channel-specific sensor decorators / pipelines |
| **SIA Core Adapter** | Defines strict `SIACore` Protocol; provides test `MockSIA` | Python `typing.Protocol` |
| **Oracle** | Computes reference safety envelope and expected responses from Ground Truth | Deterministic domain rule engine |
| **Evaluator** | Compares SIA decision stream against Oracle targets | Scoring engine producing structured `EvaluationResult` |
| **RunRecorder** | Captures telemetry stream for inspection and regression comparisons | Polars DataFrame writer to Parquet/JSON Lines |

## Recommended Project Structure

```text
sia-sim/
├── pyproject.toml              # Build & dependency configuration (uv)
├── README.md                   # Project overview & quickstart
├── src/
│   └── sia_sim/
│       ├── __init__.py
│       ├── core/               # Fundamental protocols, clock, and runner
│       │   ├── clock.py
│       │   ├── protocols.py
│       │   └── runner.py
│       ├── contracts/          # Strict Pydantic models (CORE-002..006)
│       │   ├── sensor_frame.py
│       │   ├── ground_truth.py
│       │   ├── scenario.py
│       │   ├── decision.py
│       │   └── evaluation.py
│       ├── world/              # Environment & physical vessel dynamics
│       │   ├── environment.py
│       │   ├── dynamics.py
│       │   └── world_model.py
│       ├── sensors/            # Sensor modeling, noise, and faults
│       │   ├── base.py
│       │   ├── models.py
│       │   └── noise.py
│       ├── sia_adapter/        # SIA Core protocol & MockSIA
│       │   ├── adapter.py
│       │   └── mock_sia.py
│       ├── evaluation/         # Oracle rules & Evaluator
│       │   ├── oracle.py
│       │   └── evaluator.py
│       └── storage/            # Run recorder & telemetry export
│           └── recorder.py
├── scenarios/                  # Golden and test scenario definitions
│   └── sim_005_broach.json
├── tests/                      # Automated test suite
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_contracts.py
│   │   ├── test_clock.py
│   │   ├── test_dynamics.py
│   │   └── test_sensors.py
│   └── integration/
│       └── test_golden_sim005.py
└── runs/                       # Output artifact directory (telemetry, reports)
```

## Architectural Boundaries and Invariants

1. **Information Barrier**: No object of type `GroundTruthFrame` or reference to `WorldModel` may be imported or accessible in `sia_adapter` or `sia_sim.sia_adapter.mock_sia`.
2. **Determinism**: Given `(scenario, seed)`, two successive executions must produce bit-for-bit identical telemetry, Oracle results, and Evaluation outputs.
3. **Immutability of In-Flight Frames**: Frames passed between components should be frozen/read-only to prevent back-channel mutations.
