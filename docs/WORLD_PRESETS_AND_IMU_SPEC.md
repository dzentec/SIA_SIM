# Marine World Presets, Continuous Living Sea Physics, IMU Sampling & Gauge Damping Specification

**Document Version:** 1.0.0  
**Related Documents:** `SIA_PRD_IMU_diff.md` (v1.1.0), `SIA-SIM-CORE.md`, `SIA-SIM-CORE-003-SENSOR & WORLD MODEL CONTRACT.md`

---

## 1. Continuous Living Sea Background Physics ("Мир шумит непрерывно")

### 1.1 Architectural Principle
The simulation ocean and atmosphere operate as a **continuous, living hydrodynamic and aerodynamic field**. The vessel is immediately underway and dynamically interacting with the ambient sea state from $T=0\text{ ms}$:
* **No Artificial Stagnation:** The vessel does not sit statically waiting for discrete timeline events.
* **Continuous Wave Excitations:** Deep-water linear wave kinematics continuously apply Froude-Krylov rolling and pitching excitation moments to the 4-DoF rigid hull:
  $$\eta(x, y, t) = \frac{H_s}{2} \cos\left(k(x \cos\mu + y \sin\mu) - \omega_0 t\right)$$
  $$K_{\text{wave\_bg}}(t) = m \cdot g \cdot \overline{GM}_T \cdot \text{slope}_{\text{transverse}}(t) \cdot C_{\text{Smith}}$$
* **Natural Wind Turbulence:** Continuous multi-harmonic turbulence ($\approx 4\text{–}8\%$ amplitude) is superimposed onto the base true wind speed ($TWS$) and true wind angle ($TWA$).
* **Clean Sailing with Empty Timeline:** When no scenario events are placed on the timeline, the vessel sails continuously and stably in that preset's natural sea state.

### 1.2 Timeline as an Anomaly / Hazard Layer
The interactive timeline is purely a mechanism for injecting discrete situational hazards or equipment faults onto the living sea background:
* **Wave Slam / Impact:** Heavy breaking rogue waves with localized hydrodynamic impact forces ($>10\text{ kN}$).
* **Wind Gust / Microburst:** Abrupt wind speed strikes ($\Delta TWS > 15\text{ kt}$) and directional shifts.
* **Sensor Faults:** IMU hardware lockups, GPS fix loss, anemometer freeze.

---

## 2. The 4 Canonical Marine World Presets

| Preset Identifier | Sea State | Base TWS | Wave $H_s$ | Wave Period $T$ | Initial SOG | Base Working Heel | Dynamic Characteristics |
|---|---|---|---|---|---|---|---|
| **`PRESET-HARBOUR`** | Calm (Beaufort 2) | $4.0\text{ kt}$ | $0.2\text{ m}$ | $3.0\text{ s}$ | $2.5\text{ kt}$ | $-1.5^\circ$ | Smooth motoring/gentle ripple, zero slamming, minimal motion. |
| **`PRESET-COASTAL-CRUISE`** | Moderate (Beaufort 4) | $13.0\text{ kt}$ | $1.0\text{ m}$ | $4.5\text{ s}$ | $5.8\text{ kt}$ | $-12.0^\circ$ | Ideal reaching conditions, lively gentle roll/pitch oscillations. |
| **`PRESET-FRESH-BREEZE`** | Fresh (Beaufort 6) | $21.0\text{ kt}$ | $2.1\text{ m}$ | $5.0\text{ s}$ | $7.2\text{ kt}$ | $-20.0^\circ$ | Steep short chop, dynamic wave moments, periodic light slamming ($3\text{–}6\text{ kN}$). |
| **`PRESET-GALE-BROACH`** | Gale (Beaufort 7+) | $28.0\text{ kt}$ | $3.2\text{ m}$ | $6.5\text{ s}$ | $8.5\text{ kt}$ | $-24.0^\circ$ | Severe seas, high capsize leverage, broach onset threshold. |

### 2.1 Custom World Parameters
Users can customize and run simulations with arbitrary environmental parameters via the `custom_world` configuration or the Workbench **⚙️ Custom Sea** interface:
* `initial_tws_kt` ($0\text{–}60\text{ kt}$)
* `initial_twa_deg` ($0\text{–}359^\circ$)
* `initial_wave_height_m` ($0\text{–}15\text{ m}$)
* `initial_wave_period_s` ($1\text{–}25\text{ s}$)
* `initial_sog_kt`, `initial_heading_deg`, `initial_heel_deg`

---

## 3. IMU Sampling & Edge Architecture (RFC `SIA-PRD-IMU v1.1.0`)

In accordance with approved RFC `SIA_PRD_IMU_diff.md`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             MCU SENSOR NODE                                 │
│                                                                             │
│  [MEMS Sensor 100 Hz]                                                       │
│          │                                                                  │
│          ▼                                                                  │
│  [Digital LPF (20/40 Hz)] ──► [MCU Ring Buffer] ──► [Edge Peak Computer]    │
│                                       │                      │              │
└───────────────────────────────────────┼──────────────────────┼──────────────┘
                                        ▼                      ▼
                           [NAV_DATA Stream]          [PEAK_ENVELOPE Packet]
                           • 100 Hz (MCU Raw)         • Max roll rate
                           • 50 Hz (RS-485)           • Max slamming g-force
                           • 10 Hz (Wireless RF)      • Event triggers (P0)
```

### 3.1 Sampling Modes
1. **100 Hz (MCU Internal Raw):** Full-bandwidth internal acquisition clock.
2. **50 Hz (RS-485 Wired Mode):** High-density wired telemetry stream.
3. **10 Hz (`NAV_DATA` Wireless RF):** Ultra-low-power radio broadcast (TDMA $\le 2\text{ ms}$ synchronization, $\ge 30$ days battery endurance).
4. **20 Hz:** Intermediate telemetry rate.

### 3.2 Anti-Vibration Hardware LPF (§2.3 MOD-03)
A digital 1st/2nd-order low-pass filter with cut-off frequency $f_c = 20\text{ Hz}$ or $40\text{ Hz}$ eliminates engine harmonics and high-frequency mounting resonance:
$$\alpha = \frac{2\pi f_c \Delta t}{1 + 2\pi f_c \Delta t}$$
$$y[n] = y[n-1] + \alpha (x[n] - y[n-1])$$

### 3.3 Edge Peak Computing (`PEAK_ENVELOPE`, §2.1 MOD-01)
Even when downsampled to 10 Hz, the sensor node retains an internal 100 Hz peak-hold accumulator for acceleration magnitude and roll rate, ensuring short transient slamming shocks ($10\text{–}50\text{ ms}$) are never lost due to Nyquist decimation.

---

## 4. Physical Marine Instrument Damping (Raymarine / B&G Standard)

### 4.1 Mechanical & Electronic Damping Model
Physical marine dial gauges (apparent wind, compass, inclinometers, G-meters) do not jump nervously on raw 100 Hz sensor ticks. They incorporate silicone mechanical damping fluid and electronic exponential smoothing:
$$\theta_{\text{needle}}(t) = \theta_{\text{needle}}(t - \Delta t) + \left(1 - e^{-\Delta t / \tau}\right) \left(\theta_{\text{target}} - \theta_{\text{needle}}(t - \Delta t)\right)$$

### 4.2 Damping Profiles
* **Normal ($\tau = 0.35\text{ s}$):** Default B&G / Raymarine instrument standard. Crisp yet organic needle response.
* **Heavy ($\tau = 0.75\text{ s}$):** Heavy offshore damping for severe storm conditions.
* **Direct Raw ($\tau = 0.001\text{ s}$):** Instantaneous un-damped debugging mode.
* **Rendering:** Dial needles are animated smoothly at 60 FPS via `requestAnimationFrame` decoupled from the simulation step frequency.
