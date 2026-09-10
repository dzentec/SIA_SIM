<!-- GSD:project-start source:PROJECT.md -->

## Project

**SIA Simulation**

SIA Simulation is a deterministic, local physics- and sensor-driven simulation testbed for validating the Safety & Intelligence Architecture (SIA) Core. It generates synthetic vessel dynamics, environmental conditions, and sensor observations (SensorFrame) at 100 Hz, feeding them to SIA Core while independently verifying SIA responses against Ground Truth and physical safety constraints using an Oracle and Evaluator.

**Core Value:** The single most critical requirement: strictly maintain the system boundary where only `SensorFrame` enters SIA Core, ensuring deterministic end-to-end execution of the Broach Precursor scenario (SIM-005) with automated Oracle evaluation and reproducible PASS/FAIL verification without simulation ever making decisions on behalf of SIA.

### Constraints

- **Tech Stack**: Python 3.12+, `uv` package manager, Pydantic, NumPy/SciPy, Polars/PyArrow, pytest.
- **Architecture Boundary**: Hard boundary — SIA Core must never access `GroundTruthFrame`, `WorldState`, Dynamics state, or Oracle internals.
- **Determinism**: Fully deterministic execution driven by discrete simulation clock (10 ms / 100 Hz tick) and explicit PRNG seeds; zero reliance on wall-clock time.
- **Performance**: Capable of running faster than real-time for batch test execution.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Core runtime | Strong typing support (PEP 695 type aliases, modern typing syntax), high performance, robust mathematical ecosystem |
| uv | latest (0.6+) | Package & environment management | Sub-second virtualenv setup, deterministic lockfiles (`uv.lock`), seamless Python toolchain execution |
| Pydantic | 2.13.5 (v2.x) | Data contracts, validation & serialization | High-speed Rust-backed validation (`pydantic-core`), strict schema enforcement for `SensorFrame`, `GroundTruthFrame`, `Scenario` |
| NumPy | 2.5.3 (2.x) | Vectorized physics, math & transforms | Industry standard for numerical operations, rigid-body coordinate conversions, deterministic array operations |
| SciPy | 1.18.1 | Numerical integration & spatial kinematics | High-precision ODE solvers (`solve_ivp` with deterministic RK4/Euler steps) and rotation transformations |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Polars | 1.44.1 | Telemetry log processing & batch analytics | Ingestion, filtering, and metric calculation on high-frequency (100 Hz) simulation runs |
| PyArrow | 25.0.1 | Parquet serialization | Compact, zero-copy on-disk storage for telemetry, traces, and replay logs |
| pytest | latest (8.x) | Test runner and harness | Fast, extensible testing for contracts, physics invariants, and scenario verifications |
| hypothesis | latest (6.x) | Property-based testing | Fuzzing data contracts, physics boundary conditions, and sensor fault generators |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff | Fast linter and formatter | Replaces flake8, black, isort; keeps code strictly typed and clean |
| mypy | Static type checking | Enforces strict typing across all interfaces and protocols |

## Installation

# Initialize uv project with Python 3.12+

# Core dependencies

# Dev dependencies

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `uv` | `poetry` / `pipenv` | Only if legacy CI/CD environments cannot install standalone Rust binaries |
| Pydantic v2 | `msgspec` / `dataclasses` | `dataclasses` is lighter, but lacks automated runtime schema validation and contract constraints |
| NumPy / SciPy | C++ / Rust bindings | Only needed if 100 Hz simulation cannot run >10x real-time in pure Python (premature optimization for MVP) |
| Polars | Pandas | Never for new 2026 pipelines; Polars is 10-50x faster with lower memory footprint |

## What NOT to Use

- **ROS2 / Gazebo**: Overkill and non-deterministic overhead for an MVP algorithmic validation loop.
- **CFD / OpenFOAM**: Too slow for batch scenario execution; simplified engineering hydrodynamic equations are sufficient.
- **AsyncIO / Threading in Core Loop**: The core loop must be synchronous and step-based to guarantee deterministic order of execution.
- **Real-time wall-clock delays (`time.sleep`)**: Time must strictly advance via simulated discrete ticks (`clock.advance(10)`).

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
