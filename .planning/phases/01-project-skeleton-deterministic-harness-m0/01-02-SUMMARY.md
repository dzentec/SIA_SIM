---
phase: 01-project-skeleton-deterministic-harness-m0
plan: 02
subsystem: core
tags: [clock, rng, determinism, simulation_clock, 100hz, seedsequence]

requires:
  - phase: 01-project-skeleton-deterministic-harness-m0
    provides: "Base environment, pytest runner, pyproject.toml"
provides:
  - "SimulationClock: deterministic 100 Hz discrete integer time authority"
  - "RNGManager: isolated multi-channel PRNG stream manager"
affects:
  - "Phase 2 (Data Contracts)"
  - "Phase 3 (World & Dynamics)"
  - "Phase 4 (Sensor Model)"

actuals:
  tokens: 2100
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "SimulationClock with SimulationClockProtocol"
    - "RNGManager using NumPy SeedSequence & PCG64"
  patterns:
    - "Discrete integer millisecond time step progression (tick_ms=10)"
    - "Deterministic channel hashing for cross-channel PRNG independence"

key-files:
  created:
    - src/sia_sim/core/clock.py
    - src/sia_sim/core/rng.py
    - src/sia_sim/core/__init__.py
    - tests/unit/test_clock.py
    - tests/unit/test_rng.py
  modified:
    - pyproject.toml

key-decisions:
  - "Prohibit negative time step advances or wall-clock imports"
  - "Hash channel names with SHA-256 for deterministic child SeedSequence spawning"

requirements-completed:
  - SKEL-02
  - SKEL-03

coverage:
  - id: D1
    description: "SimulationClock discrete 100 Hz integer step progression"
    requirement: "SKEL-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_clock.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "RNGManager isolated cross-channel PRNG determinism"
    requirement: "SKEL-03"
    verification:
      - kind: unit
        ref: "tests/unit/test_rng.py"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-09-11
status: complete
---

# Plan 01-02 Summary: Deterministic Clock & PRNG Harness

**Implemented `SimulationClock` (100 Hz / 10 ms integer tick) and `RNGManager` (channel-isolated NumPy PRNG) with unit verification confirming complete determinism and absence of wall-clock drift.**

## Accomplishments

- Implemented `SimulationClockProtocol` and `SimulationClock` in `src/sia_sim/core/clock.py` maintaining discrete integer time (`time_ms`), validating step sizes, and supporting clean resets without wall-clock dependencies.
- Implemented `RNGManager` in `src/sia_sim/core/rng.py` using `np.random.SeedSequence` with deterministic channel hashing (`get_channel`), ensuring that sampling from one channel (e.g. `imu`) never affects the pseudorandom sequence of another (e.g. `wind`).
- Created unit tests in `tests/unit/test_clock.py` (7 tests) and `tests/unit/test_rng.py` (6 tests).
- All 15 tests in the test suite pass with 100% success; ruff and mypy pass with 0 errors.
