---
phase: "09"
plan: "02"
title: "Sail Aerodynamics & 3D Center of Effort Engine"
status: "COMPLETED"
completed_at: "2026-09-16T23:52:00+03:00"
requirements:
  - SAIL-01
  - SAIL-02
  - SAIL-03
  - SAIL-04
  - SAIL-05
  - SAIL-06
---

# Plan 09-02 Summary: Sail Aerodynamics & 3D Center of Effort Engine

## Overview
Successfully implemented a physics-based multi-component 3D sail aerodynamics engine in [src/sia_sim/physics/sails/](file:///d:/Tasks/My/SIA/simulation/src/sia_sim/physics/sails/) adhering to the Sail Physics Specification. The engine models individual sails as 3D lifting bodies with dynamic geometric coordinates (tack, head, clew), angle of attack tracking $\alpha = |\text{AWA}| - |\theta_{\text{boom}}|$, dynamic 3D Center of Effort ($CoE_x, CoE_y, CoE_z$) shift under boom easing and reefing, downwind mainsail blanketing, upwind slot effect (Venturi acceleration), and cross-product 3D aerodynamic moments ($\vec{M} = \sum \vec{r}_i \times \vec{F}_i$).

## Deliverables & Key Changes

1. **`Sail` Object Model & Dynamic 3D CoE Kinematics (`src/sia_sim/physics/sails/sail.py`)**:
   - Implemented `SailConfig`, `SailEvaluationResult`, and `Sail` classes.
   - Dynamic boom/clew angle kinematics $\theta_{\text{boom}}$ based on sheet trim ratio and apparent wind angle.
   - Dynamic 3D Center of Effort calculation:
     - Lateral shift: $y_{CoE} = y_{\text{tack}} + \frac{1}{3} L_{\text{foot}} \sin(\theta_{\text{boom}})$.
     - Vertical drop: $z_{CoE}$ lowers proportionally with reef ratio $R$.
   - 3D cross-product moment calculations:
     - $M_x = r_y F_z - r_z F_y$ (Heeling moment, + starboard roll)
     - $M_y = r_z F_x - r_x F_z$ (Pitching moment, + bow down)
     - $M_z = r_x F_y - r_y F_x$ (Yawing / weather helm moment, + starboard turning)

2. **Sail Aerodynamic Polars (`src/sia_sim/physics/sails/polars.py`)**:
   - Implemented `evaluate_sail_polar` covering `SailType`: `MAINSAIL`, `GENOA`, `JIB`, `CODE_ZERO`, `GENNAKER`, `SPINNAKER`, `STORM_JIB`.
   - Realistic 3D low-aspect vortex flow regimes: linear attached flow, stall/separation transition, and flat plate cross-flow drag.
   - Included draft/camber effects and roller furling degradation (increased drag $C_D$, reduced $C_L$).

3. **`SailRig` Interaction Engine & Extensibility Hooks (`src/sia_sim/physics/sails/rig.py`)**:
   - Implemented `SailRig` multi-sail aggregator and `create_standard_sloop_rig`.
   - Mutual aerodynamic interactions:
     - Downwind wind shadow / blanketing on $\text{TWA} > 130^\circ$ reducing headsail drive.
     - Upwind slot effect / Venturi acceleration on $\text{TWA} = 25^\circ \dots 65^\circ$ boosting mainsail $C_L$.
   - High-level preset sail plan configurations (`FULL_MAIN`, `REEF_1`, `REEF_2`, `REEF_3`, `CODE_ZERO`, `GENNAKER`, `STORM_JIB_ONLY`, `BARE_POLES`).
   - Clean decoupled extension interfaces:
     - `HullHydrodynamicsHook` (hull resistance + keel/rudder lift/drag + leeway)
     - `ApparentWindFeedbackHook` (closed-loop apparent wind incorporating mast velocity)
     - `WaveSailInteractionHook` (wave trough attenuation)
     - `SailTrimProfileHook` (furling degradation and Boom Vang twist distribution)

4. **Integration with Planar Dynamics (`forces.py` & `dynamics.py`)**:
   - `forces.sail_forces` delegates to `SailRig` for 3D multi-sail evaluation.
   - `VesselDynamics` maintains an internal `self.rig: SailRig`, supports preset sail plans and dynamic sail trimming.

5. **Unit & Integration Test Suite (`tests/unit/test_sail_aerodynamics.py`)**:
   - Unit tests covering 3D polars, boom kinematics, Center of Effort shifts, blanketing, slot effects, and extensibility hooks.
   - All 230 unit, integration, and golden tests passing cleanly.

## Verification
- `uv run pytest`: 230/230 tests passed (100%).
- `uv run ruff check`: Clean (0 errors).
- Golden SIM-005 end-to-end evaluation: **PASS** verdict with 100% safety margin and 0 false alarms.
