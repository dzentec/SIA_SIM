---
phase: "08"
slug: "sia-simulation-workbench-ui"
status: approved
shadcn_initialized: false
preset: none
created: "2026-09-15"
---

# Phase 08 — UI Design Contract: SIA Simulation Workbench

> Visual and interaction contract for the SIA Simulation Workbench single-screen interactive research and operational studio.

---

## Executive Summary & Architectural Principle

The Workbench is a **visual instrument of safety proof and causal discovery**:

$$\text{Scenario (Timeline)} \longrightarrow \text{Ground Truth (Hidden)} \longrightarrow \text{SensorFrame (Marine Console)} \longrightarrow \text{SIA Core (Decision + Query Loop)} \longrightarrow \text{Oracle / Evaluator (PASS/FAIL)}$$

Key Invariants locked by this specification:
1. **Hard Visual Boundary:** Ground Truth is styled as a strict laboratory terminal with explicit `● NOT AVAILABLE TO SIA` badge — never using yacht dials.
2. **Marine Cockpit Standards:** Sensor View uses authentic Raymarine / B&G marine displays with standard maritime units (knots `kt`, degrees `°`, meters `m`, port/starboard color coding).
3. **Decision Dominance:** Primary response card dominates; alternative candidate responses are compact.
4. **Interactive Query Loop:** SIA never invents missing physical context (such as reef/sail configurations) — it prompts the skipper with 1-click quick action chips.
5. **Dual Operation Mode:** Seamless toggle between `LIVE / OPERATION` (minimal high-contrast cockpit) and `DEBUG / RESEARCH` (noise matrices, latency queues, raw AST traces, Oracle margin).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable (Pure Vanilla CSS + HTML5 Canvas) |
| Component library | none (Ultra-fast 60 FPS Canvas instruments + modular custom elements) |
| Icon library | Phosphor Icons / Lucide SVG inline icons |
| Font | `JetBrains Mono` (telemetry/code/terminal) + `Inter` (UI/copy) |

---

## Spacing Scale

Declared values (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Dial ticks, compact tag padding, icon gaps |
| sm | 8px | Button inline padding, chip gaps, card internal padding |
| md | 16px | Standard grid gap, widget margins |
| lg | 24px | Section dividers, header margins |
| xl | 32px | Major column gaps |
| 2xl | 48px | Timeline track vertical padding |
| 3xl | 64px | Page container maximum padding |

Exceptions: 2px border radius on precise measurement ticks.

---

## Typography

| Role | Size | Weight | Line Height | Font Family |
|------|------|--------|-------------|-------------|
| Display | 32px | 700 | 1.2 | `Inter`, sans-serif |
| Heading | 20px | 600 | 1.3 | `Inter`, sans-serif |
| Subheading | 15px | 600 | 1.4 | `Inter`, sans-serif |
| Body | 13px | 400 | 1.5 | `Inter`, sans-serif |
| Label | 11px | 500 | 1.2 | `Inter`, sans-serif (Uppercase, tracking +0.05em) |
| Telemetry Value | 22px | 700 | 1.1 | `JetBrains Mono`, monospace |
| Telemetry Unit | 12px | 400 | 1.1 | `JetBrains Mono`, monospace |
| Terminal Monospace | 12px | 400 | 1.4 | `JetBrains Mono`, monospace |

---

## Color Palette (Night Bridge / Marine Cockpit)

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#080c14` | Deep maritime midnight background, outer shell |
| Secondary (30%) | `#111827` / `#162032` | Surface panels, dial bezels, card backgrounds |
| Surface Border | `#1f2d47` | Widget outlines, timeline grid lines |
| Primary Accent (10%) | `#00e5ff` (Cyan) | Active timeline cursor, selected response highlight, SOG vector |
| Marine Starboard | `#00e676` (Green) | Right-hand wind sector ($0^\circ \dots 180^\circ$), healthy sensor status |
| Marine Port | `#ff1744` (Red) | Left-hand wind sector ($-180^\circ \dots 0^\circ$), critical hazard alert |
| Advisory Warning | `#ffb300` (Amber) | Elevated risk ($18^\circ \le \text{Heel} < 25^\circ$), unconfirmed query loop |
| Ground Truth Tint | `#94a3b8` / `#64748b` | Muted slate monochrome for physics telemetry (signaling locked state) |

Accent reserved for:
- Timeline playback cursor and event drag handles.
- Primary recommended response card border.
- Active interactive Quick Action choice button in Query Loop.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary Run CTA | `▶ Run Simulation` |
| Pause CTA | `⏸ Pause Simulation` |
| Reset CTA | `↺ Reset State` |
| Step CTA | `⏯ Step (10 ms)` |
| Mode Toggle (Live) | `● LIVE / OPERATION` |
| Mode Toggle (Debug)| `○ DEBUG / RESEARCH` |
| Ground Truth Badge | `● SIMULATION ONLY — NOT AVAILABLE TO SIA` |
| Sensor View Badge | `● SENSOR FRAME — OBSERVED BY SIA` |
| SIA Header (Nominal)| `STATUS: NOMINAL (NO HAZARD)` |
| SIA Header (Alert)  | `⚠ BROACH PRECURSOR DETECTED — CRITICAL` |
| Query Prompt        | `SIA: "Cannot determine sail configuration from sensors. Specify current set:"` |
| Query Actions       | `[ FULL MAIN ]` `[ REEF 1 ]` `[ REEF 2 ]` `[ STORM JIB ONLY ]` |
| Recalculation Note  | `SIA: Context updated → Decision recalculated` |
| Empty State Heading | `No Active Simulation` |
| Empty State Body    | `Select a scenario from presets or place events on the timeline to begin.` |
| Sensor Fault Copy   | `GPS: NO FIX / SIGNAL LOST` / `IMU: HARDWARE FAULT` |
| Evaluator Verdict PASS | `VERDICT: PASS (M4) — Safety Envelope Maintained (Margin: {N}%)` |
| Evaluator Verdict FAIL | `VERDICT: FAIL — Safety Envelope Breached at T={N}s` |

---

## 5-Zone Layout Structure

```
+-------------------------------------------------------------------------------------------------------------------------+
| [HEADER BAR] SIA Simulation Workbench   [Preset: SIM-005 Broach Precursor]   [T=00:04.20]  [▶ Run] [⏸ Pause] [↺ Reset] [⚙]  |
+-------------------------------------------------------------------------------------------------------------------------+
| [ZONE 1: TIMELINE & TEMPORAL DEBUGGER]                                                                                  |
|  Tracks: Wind Gusts | Waves | Sensor Faults | Rudder Action | SIA Decision Points | Scrub Cursor                        |
+------------------------------+----------------------------------+-------------------------------------------------------+
| [ZONE 2: GROUND TRUTH]       | [ZONE 3: SENSOR VIEW]            | [ZONE 4: SIA ADVISORY & REASONING]                    |
| Monospace Lab Monitor        | Marine B&G Dial Console          | Decision Hierarchy: Primary + Alternatives            |
| TWS, TWD, Waves, True Heel   | AWA/AWS Wind Dial, Heel IMU,     | 1. BEAR AWAY (Score 0.95, Rudder -15°)                |
| Rudder Hydro Loss            | SOG/COG, Sensor Health L0        | 2. EASE MAIN (Score 0.85)                             |
| ● NOT AVAILABLE TO SIA       | ● INPUT TO SIA                   | 3. ALERT CREW (Score 0.70)                            |
+------------------------------+----------------------------------+-------------------------------------------------------+
| [ZONE 5: INTERACTION & QUERY LOOP]                                                                                      |
|  SIA Context Question: "Specify sail set: [ FULL MAIN ] [ REEF 1 ] [ REEF 2 ] [ STORM ]"                                 |
|  Skipper Action: [ REEF 1 ]  -->  SIA: Recalculated decision                                                            |
+-------------------------------------------------------------------------------------------------------------------------+
| [FOOTER: ORACLE & EVALUATOR STATUS]                                                                                     |
|  Oracle Envelope: INTACT │ Detection Latency: 240 ms (Target <500 ms) │ False Alarms: 0 │ Verdict: [ PASS (M4) ]        |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## UI Considerations & State Coverage

| Category | Element | Status | Resolution / Specification |
|----------|---------|--------|----------------------------|
| Loading / Init | Workbench Shell | ✅ covered | Preloads default SIM-005 scenario at T=0; dials render neutral zero positions |
| Empty state | Scenario Timeline | ✅ covered | Displays empty track guidance: "Click anywhere on track to add Gust / Wave / Fault" |
| Interactive Query | Query Loop Box | ✅ covered | Hidden when confidence is high; animates smoothly into focus with quick action chips on anomaly |
| Scrubbing / Pause | Temporal Debugger | ✅ covered | Pauses simulation clock; dragging scrub cursor updates all 3 columns simultaneously at 100 Hz step |
| Sensor Fault state | Instrument Dials | ✅ covered | Dial needle dims, display shows `---` or amber `NO FIX` badge; never coerces to 0.0 |
| Overflow | Decision Candidates | ✅ covered | Fixed 3-candidate slot allocation prevents vertical layout shifts |

---

## Registry & Block Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| Vanilla Framework | Canvas 2D + Custom CSS Grid | not required (Zero external UI dependencies) |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS (Explicit maritime terms, neutral decision framing)
- [x] Dimension 2 Visuals: PASS (Strict boundary distinction: Lab Terminal vs Marine Console)
- [x] Dimension 3 Color: PASS (Night bridge 60-30-10 palette with port/starboard accents)
- [x] Dimension 4 Typography: PASS (Dual typography: JetBrains Mono for telemetry + Inter for UI)
- [x] Dimension 5 Spacing: PASS (Strict 4px multiple scale)
- [x] Dimension 6 Registry Safety: PASS (Pure native implementation)
- [x] Dimension 7 Inventory Provenance: PASS (Clean self-contained component inventory)

**Approval:** approved 2026-09-15
