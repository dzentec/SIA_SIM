# Phase 08 — UI Design & Specification Review: SIA Simulation Workbench

> **Review Type:** 6-Pillar Visual & Interaction Contract Audit  
> **Target Artifact:** `08-UI-SPEC.md` / `SIA_WORKBENCH_UI_SPEC.md`  
> **Status:** APPROVED (Score: 24/24)  
> **Audited Date:** 2026-09-15

---

## 1. Executive Summary

The UI specification for Phase 08 (**SIA Simulation Workbench**) provides a single-screen operational and causal research cockpit. It translates the deterministic 100 Hz simulation testbed into an interactive tool for naval architects, SIA algorithmic researchers, and vessel skippers.

The design enforces the core project invariant: **Ground Truth physics and Sensor observations are strictly visually and architecturally segregated.**

---

## 2. Six-Pillar Graded Assessment

| Pillar | Score | Status | Key Highlights |
|---|:---:|:---:|---|
| **1. Copywriting & Domain Precision** | **4 / 4** | **EXCELLENT** | Rigorous maritime standard units (`kt`, `°`, `m`, `s`), explicit port/starboard naming, clear distinction between Ground Truth badge (`● SIMULATION ONLY — NOT AVAILABLE TO SIA`) and Sensor badge (`● SENSOR FRAME — OBSERVED BY SIA`). |
| **2. Visual Hierarchy & Layout** | **4 / 4** | **EXCELLENT** | 5-Zone structured layout: Top Control Bar $\rightarrow$ Zone 1 Temporal Debugger Track $\rightarrow$ 3-Column Core (Ground Truth vs Marine Dial Console vs SIA Reasoning) $\rightarrow$ Zone 5 Interactive Query Loop $\rightarrow$ Evaluator Footer. |
| **3. Color & Theme System** | **4 / 4** | **EXCELLENT** | 60-30-10 Night Bridge palette (`#080c14` background, `#111827` panels, `#00e5ff` cyan accent). Functional maritime starboard green (`#00e676`), port red (`#ff1744`), and advisory amber (`#ffb300`). |
| **4. Typography & Readability** | **4 / 4** | **EXCELLENT** | Dual-type system: `JetBrains Mono` for jitter-free tabular telemetry/timestamps; `Inter` for operational copy and structured hierarchy. |
| **5. Spacing & Rhythm** | **4 / 4** | **EXCELLENT** | Consistent 4px modular spacing scale (`4px` to `64px`), eliminating vertical layout shifts with fixed 3-slot candidate allocations. |
| **6. Experience & Interaction Design** | **4 / 4** | **EXCELLENT** | Interactive scrubber with 100 Hz step synchronization, Live vs. Debug mode toggle, robust sensor fault states (dials show `---`, no coercion to 0.0), and 1-click skipper query action chips. |

**Overall Score: 24 / 24 (100%)**

---

## 3. Structural & Invariant Verification

### Hard Visual Boundary
- **Ground Truth Terminal (Zone 2):** Styled strictly as a slate/monospaced laboratory terminal (`#64748b`/`#94a3b8`). Never uses yacht instruments, visually communicating that this is hidden world state.
- **Sensor Console (Zone 3):** Modeled after authentic Raymarine / B&G yacht electronics (circular AWA/AWS dial, heel inclinometer, SOG/COG vectors, sensor health indicators).

### Interactive Query Loop
- Implements the skipper-in-the-loop paradigm: when SIA cannot infer physical state (e.g. unknown reef configuration), it prompts with 1-click action chips (`[ FULL MAIN ]`, `[ REEF 1 ]`, `[ REEF 2 ]`, `[ STORM JIB ]`), instantly recalculating decision candidates without simulation stalls.

### Dual Operational Mode
- **LIVE / OPERATION:** Minimalist, high-contrast dark bridge mode suitable for real-time monitoring and situational awareness.
- **DEBUG / RESEARCH:** Full laboratory mode displaying noise matrices, sensor degradation latency queues, raw AST inspection badges, and Oracle safety margins.

---

## 4. Implementation Readiness & Next Actions

The `08-UI-SPEC.md` specification is complete, verified against all GSD design standards, and ready for plan creation and implementation.

**Recommended Workflow Path:**
1. `/gsd-plan-phase 08` — Create detailed implementation plans (Canvas instruments, state manager, timeline scrubber, SIA query loop).
2. `/gsd-execute-phase 08` — Implement the standalone HTML5/Vanilla CSS/Canvas Workbench studio.
