---
phase: 04-deterministic-sensor-degradation-fault-verification-m3
plan: 01
subsystem: sensors
tags: [sensors, degradation, noise, bias, drift, latency, fault_modes, imu, gps, wind, actuator]

requires:
  - phase: 03-simplified-deterministic-causal-vessel-dynamics-m2
    provides: "VesselState and EnvironmentState physical models"
provides:
  - "ChannelDegrader: deterministic Gaussian noise, bias, drift, latency queue, and fault primitives"
  - "IMUSensorModel, GPSSensorModel, WindSensorModel, ActuatorSensorModel channel models"
affects:
  - "04-02-PLAN"
  - "04-03-PLAN"
  - "Phase 5 (SIACore Boundary)"

actuals:
  tokens: 2400
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "Sensor degradation engine with isolated PRNG channels"
  patterns:
    - "FIFO latency queues with discrete tick delays"
    - "Strict null semantics for sensor dropouts and absent mainsheet hardware"

key-files:
  created:
    - src/sia_sim/sensors/degradation.py
    - src/sia_sim/sensors/imu.py
    - src/sia_sim/sensors/gps.py
    - src/sia_sim/sensors/wind.py
    - src/sia_sim/sensors/actuator.py
    - src/sia_sim/sensors/__init__.py
  modified: []

key-decisions:
  - "Enforce None semantics on missing or failed sensor signals without zero-coercion"
  - "Default mainsheet_pct to None representing standard yacht hardware baseline"

requirements-completed:
  - SENS-01
  - SENS-02

coverage:
  - id: D1
    description: "Core degradation primitives (noise, bias, drift, latency, faults)"
    requirement: "SENS-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_sensor_channels.py"
        status: pass
      human_judgment: false
  - id: D2
    description: "Individual channel sensor models (IMU, GPS, Wind, Actuator)"
    requirement: "SENS-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_sensor_channels.py"
        status: pass
      human_judgment: false

duration: 3min
completed: 2026-09-15
status: complete
---

# Plan 04-01 Summary: Core Sensor Degradation Primitives & Channel Models

**Implemented core sensor degradation primitives (`ChannelDegrader`) and channel generators (`IMUSensorModel`, `GPSSensorModel`, `WindSensorModel`, `ActuatorSensorModel`) with channel-isolated PRNG streams.**

## Accomplishments

- Implemented `ChannelDegrader` and `DegradationConfig` in `src/sia_sim/sensors/degradation.py`.
- Implemented individual channel models in `imu.py`, `gps.py`, `wind.py`, and `actuator.py`.
- Enforced strict `None` semantics for dropouts and absent mainsheet sensor telemetry.
- Created package exports in `src/sia_sim/sensors/__init__.py`.
