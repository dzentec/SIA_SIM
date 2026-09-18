# Roadmap: SIA Simulation

## Overview

This roadmap delivers the MVP Milestone (M0–M6) for SIA Simulation: an end-to-end, deterministic 100 Hz simulation testbed that validates the Safety & Intelligence Architecture (SIA) Core. The journey progresses systematically through horizontal engineering layers—from tooling and strict data contracts, through simplified deterministic causal vessel dynamics and sensor degradation models, to strict boundary adapters, independent oracle evaluation, and the complete end-to-end pipeline PASS on the SIM-005 Broach Precursor scenario.

## Phases

- [x] **Phase 1: Project Skeleton & Deterministic Harness (M0)** - Python 3.12+, uv, strict typing, 100 Hz simulation clock, and deterministic test runner.
- [x] **Phase 2: Data Contracts & Validation (M1)** - Strict Pydantic schemas for SensorFrame, GroundTruthFrame, Scenario, and evaluation contracts.
- [x] **Phase 3: Simplified Deterministic Causal Vessel Dynamics (M2)** - Environmental wind/wave models and simplified deterministic causal vessel dynamics at 100 Hz.
- [x] **Phase 4: Deterministic Sensor Degradation & Fault Verification (M3)** - Transform ground truth to SensorFrame with deterministic noise, bias, drift, latency, and fault modes.
- [x] **Phase 5: SIACore Boundary & Deterministic MockSIA (M4)** - Strict boundary isolation protocol (`SIACore`) and deterministic `MockSIA` with candidate responses and conflict resolution.
- [x] **Phase 6: Oracle & Evaluator (M5)** - Independent physical safety oracle and objective PASS/FAIL evaluator.
- [x] **Phase 8: SIA Simulation Workbench UI** - Single-screen night bridge cockpit, 6-dial marine console, 100 Hz lab terminal, and event timeline builder.
- [x] **Phase 9: Architecture Decoupling, Modular Frontend & 3D Sail Aerodynamics Engine** - Frontend ES-modularization, physics/sails submodule with individual sails, dynamic 3D CoE & boom kinematics, and MDA v2.2 safety channel status.

- [x] **Phase 10: B&G SailSteer Navigation Display** - Authentic B&G SailSteer display widget and sliding mode toggle.
- [ ] **Phase 11: Real Marine Data Engine (DAE) & Tactical Chartplotter** - Data Acquisition Engine (Open-Meteo, GEBCO bathymetry, S-57 ENC hazards), EnvironmentProvider decoupling, and Workbench Tactical Chartplotter display.
- [ ] **Phase 12: Cockpit & Rig Control System** - Deterministic state-driven rig mechanics, winch inertia, clutches, dynamic aerodynamic statuses, REST/WS Rig API with interlock preset engine, and accessible Workbench Cockpit UI (Dual-Bar Ropes, Traveler & Reefing Dock).

## Phase Details


### Phase 1: Project Skeleton & Deterministic Harness (M0)

**Goal**: Initialize repository environment with `uv`, Python 3.12+, strict tooling (ruff, mypy), deterministic 100 Hz `SimulationClock`, and isolated PRNG harness.  
**Depends on**: Nothing (first phase)  
**Requirements**: SKEL-01, SKEL-02, SKEL-03  
**Success Criteria**:  

1. Project installs and runs tests cleanly via `uv run pytest`.  
2. `SimulationClock` advances and resets deterministically in discrete 10 ms integer ticks.  
3. Two runs initialized with the same seed yield identical random sequences across all channels.  

**Plans**: 2/2 plans executed  

Plans:

- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md
- [x] 01-01: Setup `uv` project, `pyproject.toml`, dependencies, and lint/type check toolchains.
- [x] 01-02: Implement deterministic `SimulationClock` (100 Hz / 10 ms) and seed-isolated PRNG harness with unit tests.

### Phase 2: Data Contracts & Validation (M1)

**Goal**: Implement and test strict, immutable Pydantic models for all system interfaces matching CORE-002 through CORE-006 specifications.  
**Depends on**: Phase 1  
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04, CONT-05  
**Success Criteria**:  

1. `SensorFrame`, `GroundTruthFrame`, `Scenario`, `DecisionPayload`, and `EvaluationResult` pass strict schema validation.  
2. Serialization preserves explicit `None` / `UNKNOWN` states without coercing to `0.0` or `False`.  
3. Scenario engine successfully validates and freezes scenario configurations.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 02-01: Implement `SensorFrame` and `GroundTruthFrame` contract models with strict null semantics.
- [x] 02-02: Implement `Scenario`, `DecisionPayload`, and `EvaluationResult` contract models.
- [x] 02-03: Create schema validation test suite asserting edge-case rejection and immutability.

### Phase 3: Simplified Deterministic Causal Vessel Dynamics (M2)

**Goal**: Implement environmental physics (wind, gusts, sea state) and simplified deterministic causal planar vessel dynamics executing at 100 Hz.  
**Depends on**: Phase 2  
**Requirements**: PHYS-01, PHYS-02, PHYS-03  
**Success Criteria**:  

1. Environmental forces compute reproducible, strictly causal wind velocity vectors and wave encounters.  
2. Planar vessel dynamics integrate surge, sway, yaw, and roll causally under actuator and environmental forces without non-deterministic drift.  
3. Consecutive runs with identical parameters and seed produce bit-identical trajectory states.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 03-01: Implement WorldModel with causal environmental force generators (wind gusts, sea state).
- [x] 03-02: Implement simplified deterministic causal VesselDynamics equations of motion and fixed-step numerical integration.
- [x] 03-03: Create dynamics unit and determinism verification tests.

### Phase 4: Deterministic Sensor Degradation & Fault Verification (M3)

**Goal**: Implement and verify deterministic sensor degradation pipeline converting `GroundTruthFrame` into observable `SensorFrame` with realistic noise and fault injections.  
**Depends on**: Phase 3  
**Requirements**: SENS-01, SENS-02, SENS-03  
**Success Criteria**:  

1. Sensor models synthesize realistic telemetry for IMU, GPS, wind vane, and rudder angle.  
2. Configurable Gaussian noise, static bias, and gradual drift are deterministically applied per channel.  
3. Sensor dropouts and frozen values emit proper fault flags and `None` states without simulation crashes or zero-coercion.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 04-01: Implement base sensor transformation pipeline and individual sensor channels.
- [x] 04-02: Implement deterministic noise, bias, drift, latency queue, and failure mode decorators.
- [x] 04-03: Build verification tests asserting statistical repeatability and non-coercion of missing signals.

### Phase 5: SIACore Boundary & Deterministic MockSIA (M4)

**Goal**: Build architectural isolation boundary protocol and deterministic `MockSIA` capable of multi-candidate response evaluation and decision logging.  
**Depends on**: Phase 4  
**Requirements**: ADAPT-01, ADAPT-02  
**Success Criteria**:  

1. Architectural protocol strictly isolates SIA Core to receive only `SensorFrame`.  
2. Deterministic `MockSIA` evaluates sensor frames and generates reproducible risk assessments, up to 3 candidate responses, and resolved commands.  
3. Telemetry and decision traces are recorded synchronously at 100 Hz without ground truth leakage.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 05-01: Define `SIACore` Protocol and strict boundary AST enforcement tests.
- [x] 05-02: Implement deterministic `MockSIA` with risk assessment, 3 candidate responses, and conflict resolution.
- [x] 05-03: Create run recorder for logging telemetry and decision traces.

### Phase 6: Oracle & Evaluator (M5)

**Goal**: Build independent ground-truth-based safety Oracle and Evaluator to measure detection latency and produce objective PASS/FAIL verdicts.  
**Depends on**: Phase 5  
**Requirements**: EVAL-01, EVAL-02, EVAL-03  
**Success Criteria**:  

1. Oracle independently establishes safety envelope, hazard onset, and recovery constraints from ground truth.  
2. Evaluator compares SIA decisions against Oracle expectations to compute latency and error metrics.  
3. Evaluator outputs structured `EvaluationResult` with definitive PASS/FAIL verdict.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 06-01: Implement physical Oracle computing safety envelopes and hazard timing from GroundTruth.
- [x] 06-02: Implement Evaluator comparing SIA traces against Oracle targets.
- [x] 06-03: Build evaluation verification test suite covering true positives, false alarms, and timing boundaries.

### Phase 7: Complete End-to-End Pipeline PASS (M6)

**Goal**: Assemble all components into the complete end-to-end simulation loop and execute the SIM-005 Broach Precursor scenario with automated PASS verification.  
**Depends on**: Phase 6  
**Requirements**: GOLD-01, GOLD-02, GOLD-03  
**Success Criteria**:  

1. SIM-005 scenario specification loads and validates correctly.  
2. Complete end-to-end pipeline runs at 100 Hz faster than real-time from start to finish.  
3. Automated pytest test passes, confirming successful broach mitigation and PASS evaluation across the full pipeline.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 07-01: Define SIM-005 scenario specification and integrate main `SimulationRunner`.
- [x] 07-02: Run full vertical slice of SIM-005 Broach Precursor and verify PASS verdict across the end-to-end pipeline.
- [x] 07-03: Add CI regression test ensuring 100% deterministic repeatability and PASS verdict on SIM-005.

### Phase 8: SIA Simulation Workbench UI & Interactive Studio
 
 **Goal**: Build a single-screen, high-contrast night bridge operational & research cockpit featuring 6-dial 60 FPS HTML5 Canvas marine instruments (including Pitch, Heave, and Slamming), Ground Truth lab terminal, interactive multi-track timeline event builder with zoom/pan, dynamic duration configuration, and skipper query loop.  
 **Depends on**: Phase 7  
 **Requirements**: UI-01..UI-06, WB-01..WB-07  
 **Success Criteria**:  
 
 1. Local web server launches via `sia-sim --workbench` and streams 100 Hz simulation data to browser.  
 2. 5-Zone layout strictly enforces visual segregation between Ground Truth terminal (`● NOT AVAILABLE TO SIA`) and Marine Console (`● OBSERVED BY SIA`).  
 3. Marine Console renders 6 authentic marine dials: Wind (AWA/AWS), Heel (Roll), Pitch (Trim/килевая качка), SOG/COG, Heave (вертикальная качка), and Slamming (слеминг).  
 4. Multi-track temporal timeline allows interactive event placement (Wind, Wave, Faults), dragging, editing, zooming (1x-10x), and dynamic duration configuration.  
 5. SIA Advisory Panel provides continuous nominal monitoring guidelines and high-contrast decision cards with candidate priorities on hazard onset.  
 6. Interactive skipper query loop dispatches context chips (`[ REEF 1 ]`, `[ FULL MAIN ]`) to SIA Core with real-time recalculated responses.  
 
 **Plans**: 3/3 plans executed  
 
 Plans:
 
 - [x] 08-01: Workbench Backend Engine & Telemetry Streamer.
 - [x] 08-02: Workbench UI 5-Zone Shell, Canvas Marine Dials & Lab Terminal.
 - [x] 08-03: Temporal Debugger Scrubber, Interactive Query Loop, 6-Dial Suite & Event Builder.
 - [x] 08-04: Vessel Presets (Beneteau Oceanis 45 & IOR Classic) & Interactive Sail Rig Plan (Code 0 to Bare Poles) integrated with 4-DOF dynamic aerodynamics.

### Phase 9: Architecture Decoupling, Modular Frontend & 3D Sail Aerodynamics Engine

**Goal**: Eliminate architectural tension points by modularizing the Workbench frontend into ES-modules, decoupling sail aerodynamics into `physics/sails/` with isolated `Sail` instances, dynamic boom kinematics $\theta_{\text{boom}}$, 3D $CoE(x,y,z)$ coordinates, and integrating MDA v2.2 `SafetyChannelStatus`.  
**Depends on**: Phase 8  
**Requirements**: ARCH-01, ARCH-02, SAIL-01..SAIL-06, MDA-01  
**Success Criteria**:  

1. `app.js` is cleanly decomposed into `state.js`, `playback.js`, `modals.js`, and `app.js` without any external bundling dependency (pure Zero-Build ES modules).  
2. `physics/sails/` submodule provides standalone `Sail` and `RigKinematics` with nominal areas in $\text{m}^2$, dynamic boom angle $\theta_{\text{boom}}$, 3D $CoE$ displacement, and cross-product moments $\vec{M} = \sum (\vec{r}_i \times \vec{F}_i)$.  
3. Downwind blanketing ($TWA > 130^\circ$) and slot effect ($TWA = 30^\circ\dots 60^\circ$) are modeled.  
4. `SafetyChannelStatus` (`WIRED_VERIFIED`, `WIRELESS_ADVISORY`, `MIXED`) is incorporated into `SensorFrame` and sensor pipeline.  
5. All tests pass with zero regression across the existing test suite.  

### Phase 10: B&G SailSteer™ Navigation Display & Multi-View Marine Console

**Goal**: Implement the authentic B&G SailSteer™ Navigation Display widget (conforming to `SailSteer_BG.md` v2.0) with a seamless slide-mode toggle (`[ ⊞ 6 DIAL CONSOLE ]` ⟷ `[ 🧭 SAILSTEER B&G ]`) in the central block of the SIA Simulation Workbench, rendering at 60 FPS on HTML5 Canvas across 7 graphic layers with full mathematical wind triangle resolution, laylines, fixed tack/gybe sectors, and current drift vector.  
**Depends on**: Phase 9  
**Requirements**: SS-01..SS-08, UI-07  
**Success Criteria**:  

1. Central block features a smooth slide-transition viewport and header toggle between the 6-Dial Marine Console and B&G SailSteer Display.  
2. `SailSteerRenderer` implements all 7 rendering layers (Layer 0: dark background; Layer 1: rotating compass rose at `-HDG`; Layer 2: tack/gybe sectors fixed to hull; Layer 3: apparent/true wind arrows `A`/`T` and laylines; Layer 4: boat silhouette, white HDG box, neon waypoint marker; Layer 5: current drift vector; Layer 6: 5-zone UI dashboards).  
3. Complete analytical calculation of True Wind ($TWA$, $TWS$, $TWD$), Speed Through Water ($STW$), relative current drift, steering error, and time to waypoint ($ETW$) with strict null-safety.  
4. All 6 calibrated test scenarios from `SailSteer_BG.md` §7 pass visual and telemetry verification.  
5. All backend, integration, and UI tests pass with zero regressions.  

**Plans**: 3/3 plans executed  

Plans:

- [x] 10-01: SailSteer Canvas Renderer & Mathematical Engine (`sailsteer.js`).
- [x] 10-02: Workbench UI 5-Zone Layout, CSS Styling & Slide Viewport Controller (`index.html`, `workbench.css`, `app.js`).
- [x] 10-03: Live & Playback Telemetry Integration & Validation against 6 Test Scenarios (`playback.js`, tests).

### Phase 11: Real Marine Data Engine (DAE) & Tactical Chartplotter

**Goal**: Implement the Data Acquisition Engine (DAE v1.0) architecture conforming to `.init_docs/real_geo_data.md`, decoupling environment generation via `EnvironmentProvider` (`SyntheticEnvironmentProvider` and `RealGeoEnvironmentProvider`), integrating Open-Meteo, GEBCO GeoTIFF bathymetry, S-57 ENC hazard parser, and building an interactive Tactical Marine Chartplotter in the Workbench UI.  
**Depends on**: Phase 10  
**Requirements**: DAE-01..DAE-12  
**Success Criteria**:  

1. `DAE` schemas, meteorological/oceanographic vector formulas, and `UnifiedCache` (0.05° grid) pass validation and unit tests.
2. `BathymetryPipeline` reads GEBCO GeoTIFF with $2\times 2$ bilinear interpolation (safe `None` handling, never `0.0` on error).
3. `S57HazardPipeline` indexes multiple `.000` charts into Shapely `STRtree` with `CATWRK`/`VALSOU` filters and `pyproj.Geod` distance calculations.
4. `EnvironmentProvider` abstraction seamlessly switches between Synthetic and Real Geo data modes without any `SIACore` boundary leakage.
5. Simulation dead reckoning tracks vessel geographic $(lat, lon)$ coordinates at 100 Hz.
6. Workbench UI features a 3-way sliding console (`6-Dial` ⟷ `SailSteer` ⟷ `Tactical Chartplotter`) with real-time vectors, S-57 features, and night/day tactical themes.

**Plans**: 0/4 plans executed  

Plans:

- [ ] 11-01: DAE Core Contracts, Math Engine & Meteo/GRIB2 Pipeline (`schemas.py`, `cache.py`, `meteo.py`, `grib2.py`).
- [ ] 11-02: Spatial Pipelines: GEBCO Bathymetry & S-57 Hazard Spatial Index (`bathymetry.py`, `s57.py`, `assembler.py`).
- [ ] 11-03: EnvironmentProvider Abstraction, Dead Reckoning & Simulation Engine Integration (`environment.py`, `world.py`, `runner.py`, `cli.py`).
- [ ] 11-04: Tactical Marine Chartplotter Display in Workbench UI (`chartplotter.js`, `chartplotter.css`, `index.html`, `server.py`).

### Phase 12: Cockpit & Rig Control System (SIA Workbench & Physics Integration)

**Goal**: Implement the complete Cockpit & Rig Control System conforming to `.init_docs/COCKPIT & RIG CONTROL_control.md` v2.0, establishing strict data contracts (`RopeState`, `TravelerState`, `FurlerState`, `SailState`, `RigState`), realistic winch inertia & clutch physics under dynamic aerodynamic loads, REST/WS Rig API with safety-interlocked preset scenarios, and a WCAG AA-compliant, dual-channel Workbench cockpit interface with dual-bar rope widgets, centered bipolar traveler, and interactive Reefing Dock.
**Depends on**: Phase 10
**Requirements**: RIG-01..RIG-14
**Success Criteria**:

1. Strict separation of `RopeStatus` and `SailStatus` enums, signed Traveler range `[-1.0, 1.0]`, and discrete Furler kinematics (`line_trim` → `furled_ratio` → `area_ratio`).
2. Winch model implements inertia rate limits, acceleration limits, and speed degradation under heavy tension load ($1 - T_{\text{rope}}/SWL$). Clutch lock freezes `actual_trim` unconditionally.
3. Outhaul, Boom Vang, and Cunningham drive dynamic modifications to camber, twist, and stall angle without ad-hoc magic constants.
4. Rig API supports batch control inputs, state telemetry streaming, and preset orchestration with prerequisite checks (e.g. mainsheet eased check before reefing).
5. Workbench UI provides 3-column layout, dual-bar widgets (Trim & Load), centered bipolar traveler slider, modal Reefing Dock, tack-aware sheet dimming, and independent rope ID vs status color channels.

**Plans**: 4/4 plans executed

Plans:

- [x] 12-01: Rig & Sail Data Contracts, Enums & Strict Validation (`contracts/sails.py`, `tests/unit/test_sails_ropes_contracts.py`).
- [x] 12-02: Rig Kinematics, Winch Inertia & Clutch/Stopper Physics Engine (`physics/sails/rig.py`, `physics/sails/sail.py`, `tests/unit/test_rig_physics.py`).
- [x] 12-03: Rig Control JSON API & Preset Interlock Orchestrator (`web/server.py`, `engine/rig_controller.py`, `tests/integration/test_rig_api.py`).
- [x] 12-04: SIA Simulation Workbench Cockpit UI (Dual-Bar Ropes, Traveler & Reefing Dock) (`cockpit.js`, `cockpit.css`, `index.html`, `app.js`).

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Skeleton & Harness (M0) | 2/2 | Completed | 2026-09-15 |
| 2. Data Contracts & Validation (M1) | 3/3 | Completed | 2026-09-15 |
| 3. Simplified Deterministic Causal Dynamics (M2) | 3/3 | Completed | 2026-09-15 |
| 4. Deterministic Sensor Degradation & Faults (M3) | 3/3 | Completed | 2026-09-15 |
| 5. SIACore Boundary & MockSIA (M4) | 3/3 | Completed | 2026-09-15 |
| 6. Oracle & Evaluator (M5) | 3/3 | Completed | 2026-09-15 |
| 7. Complete Pipeline PASS (M6) | 3/3 | Completed | 2026-09-15 |
| 8. SIA Simulation Workbench UI | 4/4 | Completed | 2026-09-16 |
| 9. Architecture Decoupling & 3D Sails | 3/3 | Completed | 2026-09-17 |
| 10. B&G SailSteer Navigation Display | 3/3 | Completed | 2026-09-18 |
| 11. Real Marine Data Engine & Chartplotter | 0/4 | Planned | - |
| 12. Cockpit & Rig Control System | 4/4 | Completed | 2026-09-18 |

---
*Roadmap defined: 2026-09-10*
*Last updated: 2026-09-18*


