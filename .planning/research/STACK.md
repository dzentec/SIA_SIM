# Stack Research

**Domain:** Deterministic Maritime Autonomous Systems Simulation & Testbed  
**Researched:** 2026-09-10  
**Confidence:** HIGH  

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

```bash
# Initialize uv project with Python 3.12+
uv init --name sia-sim .

# Core dependencies
uv add pydantic numpy scipy polars pyarrow

# Dev dependencies
uv add --dev pytest pytest-cov hypothesis ruff mypy
```

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
