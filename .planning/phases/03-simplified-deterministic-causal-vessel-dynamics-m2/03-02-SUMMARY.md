---
phase: 03-simplified-deterministic-causal-vessel-dynamics-m2
plan: 02
subsystem: physics
tags: [physics, dynamics, forces, rk4, vessel_dynamics, 4dof, broach]

requires:
  - phase: 03-simplified-deterministic-causal-vessel-dynamics-m2
    provides: "Environmental physics and WorldModel"
provides:
  - "Aerodynamic and hydrodynamic force calculations (apparent wind, sail, rudder, damping, righting)"
  - "Fixed-step 4th-order Runge-Kutta numerical integrator (rk4_step)"
  - "VesselDynamics: 4-DOF rigid-body vessel equations of motion at 100 Hz"
affects:
  - "03-03-PLAN"
  - "Phase 4 (Sensor Degradation)"
  - "Phase 6 (Oracle)"
  - "Phase 7 (End-to-End Pipeline)"

actuals:
  tokens: 2500
  tasks: 5
  commits: 1

tech-stack:
  added:
    - "4-DOF planar vessel dynamics model with roll and rudder ventilation"
    - "Fixed-step RK4 integrator"
  patterns:
    - "Continuous state integration producing immutable VesselState at 100 Hz"

key-files:
  created:
    - src/sia_sim/physics/forces.py
    - src/sia_sim/physics/integrator.py
    - src/sia_sim/physics/dynamics.py
    - tests/unit/test_physics_forces.py
    - tests/unit/test_vessel_dynamics.py
  modified:
    - src/sia_sim/physics/__init__.py

key-decisions:
  - "Model heel-dependent rudder ventilation to naturally replicate loss-of-steerage during broaching"
  - "Integrate coupled roll-yaw dynamics to capture weather helm under severe heel"

requirements-completed:
  - PHYS-02
  - PHYS-03

coverage:
  - id: D1
    description: "Coupled aerodynamic and hydrodynamic force functions"
    requirement: "PHYS-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_physics_forces.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "4-DOF VesselDynamics RK4 integration"
    requirement: "PHYS-02, PHYS-03"
    verification:
      - kind: unit
        ref: "tests/unit/test_vessel_dynamics.py"
        status: pass
      human_judgment: false

duration: 4min
completed: 2026-09-15
status: complete
---

# Plan 03-02 Summary: Vessel Dynamics & Numerical Integrator

**Implemented coupled 4-DOF vessel dynamics (surge, sway, yaw, roll), fixed-step RK4 numerical integration, and aerodynamic/hydrodynamic force models with rudder stall and weather helm coupling.**

## Accomplishments

- Implemented `apparent_wind`, `sail_forces`, `rudder_forces`, `hydrodynamic_damping`, and `righting_moment` in `src/sia_sim/physics/forces.py`.
- Implemented fixed-step 4th-order Runge-Kutta integrator (`rk4_step`) in `src/sia_sim/physics/integrator.py`.
- Implemented `VesselDynamics` in `src/sia_sim/physics/dynamics.py` producing `VesselState` at 100 Hz.
- Verified 9 unit tests in `tests/unit/test_physics_forces.py` and 4 unit tests in `tests/unit/test_vessel_dynamics.py`.
