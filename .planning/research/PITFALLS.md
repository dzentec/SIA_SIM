# Pitfalls Research

**Domain:** Deterministic Maritime Autonomous Systems Simulation & Testbed  
**Researched:** 2026-09-10  
**Confidence:** HIGH  

## Critical Pitfalls

### Pitfall 1: Information Leakage Across the Boundary

**What goes wrong:**
Developers accidentally allow SIA Core (or MockSIA) to inspect true wind speed, true hull attitude, or Oracle expectations directly, creating tests that pass in simulation but fail catastrophically in real-world deployments.

**Why it happens:**
Convenience during debugging; passing a generic `context` object containing both `GroundTruth` and `SensorFrame`.

**How to avoid:**
1. Enforce strict type signatures: `SIACore.process(frame: SensorFrame) -> DecisionPayload`.
2. Static AST / import linter tests in `tests/` verifying that SIA adapter modules never import `GroundTruthFrame` or `WorldModel`.
3. Freeze sensor frame instances (`frozen=True` in Pydantic).

**Warning signs:**
- `MockSIA` references true vessel velocity or Oracle thresholds.
- Test fixtures sharing references across simulator and adapter.

**Phase to address:**
Phase 1 (Contracts) and Phase 4 (SIA Core Adapter).

---

### Pitfall 2: Hidden Non-Determinism (PRNG, Sets, Dict Ordering)

**What goes wrong:**
Two simulation runs with the identical seed produce slightly divergent values at step 10,000, causing flaky evaluation tests.

**Why it happens:**
1. Using global `random` or `numpy.random` instead of isolated `np.random.Generator(np.random.PCG64(seed))`.
2. Iterating over unordered `set` or unsorted keys in dictionary event triggers.
3. System time / wall-clock timestamps leaking into telemetry.

**How to avoid:**
1. Pass explicit, isolated PRNG instances (`rng: np.random.Generator`) down the call stack.
2. Use deterministic `SimulationClock.time_ms` as the sole time authority.
3. Add a dedicated regression test asserting byte-identical results over two consecutive runs with the same seed.

**Warning signs:**
- Tests that intermittently fail on CI/CD with different seeds.
- Discrepancies between run outputs on different platforms.

**Phase to address:**
Phase 0 (Skeleton/Clock) and Phase 2 (World & Dynamics).

---

### Pitfall 3: Converting NULL / UNKNOWN to 0.0 or False

**What goes wrong:**
When a sensor drops out or freezes, missing data is coerced to `0.0` (e.g. zero wind speed or zero yaw rate) or `False`. SIA Core interprets zero wind as a calm sea rather than a sensor outage, causing wrong safety interventions.

**Why it happens:**
Default values in numerical arrays or Pydantic fields defaulting to `0` or `False`.

**How to avoid:**
1. Strictly use `Optional[float] = None` or distinct status flags (`SensorStatus.DROPOUT`, `SensorStatus.VALID`).
2. Numerical models must preserve `NaN` or `None` and fail loudly if an unverified `None` is used in arithmetic.

**Warning signs:**
- Sensor failure tests show sudden drops to 0 instead of maintaining last known state or emitting fault flags.

**Phase to address:**
Phase 1 (Data Contracts) and Phase 3 (Sensor Model).

---

### Pitfall 4: Simulation Time Slipping Behind Wall-Clock / Overly Heavy ODE Solvers

**What goes wrong:**
Overcomplicating the vessel dynamics equations (e.g. using full variable-step adaptive ODE solvers with high tolerances) slows simulation down below real-time, making 100 Hz batch verification impractically slow.

**Why it happens:**
Over-engineering dynamics models before validating the control/evaluation loop.

**How to avoid:**
1. Use fixed-step numerical integration (deterministic RK4 or semi-implicit Euler at 10 ms).
2. Validate that 60 seconds of simulation time executes in < 1 second of real compute time.

**Warning signs:**
- 10-second test run takes > 5 seconds of real time.

**Phase to address:**
Phase 2 (World & Vessel Dynamics).
