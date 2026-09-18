/**
 * Cockpit & Rig Control System - SIA Simulation Workbench (v2.1 [CORRECT] Best Practices)
 * 
 * Architecture & Design:
 * - Decoupled single-rope physics evaluation without cross-rope interference
 * - Targeted single-element DOM updates (O(1) updates on drag/wheel)
 * - Independent Skipper Mode Source of Truth (no server-telemetry overwrite race conditions)
 * - Strict adherence to physical marine aerodynamics and Safe Working Loads (SWL)
 */

export const ROPE_METADATA = {
  jib_sheet_port: { name: 'Jib Sheet Port', side: 'port', badge: 'PORT', color: '#007AFF', group: 'jib' },
  furling_line: { name: 'Furling Line', side: 'port', badge: 'FURL', color: '#8E8E93', group: 'jib' },
  cunningham: { name: 'Cunningham', side: 'port', badge: 'CUNN', color: '#AEAEB2', group: 'main' },
  mainsheet: { name: 'Main Sheet', side: 'starboard', badge: 'SHEET', color: '#FF9500', group: 'main' },
  boom_vang: { name: 'Boom Vang', side: 'starboard', badge: 'VANG', color: '#FFD60A', group: 'main' },
  jib_sheet_starboard: { name: 'Jib Sheet Stbd', side: 'starboard', badge: 'STBD', color: '#34C759', group: 'jib' },
  main_halyard: { name: 'Main Halyard', side: 'deck', badge: 'HALY', color: '#FF2D55', group: 'main' },
  reef_line_1: { name: 'Reef Line 1', side: 'deck', badge: 'REEF1', color: '#FFCC00', group: 'reef' },
  reef_line_2: { name: 'Reef Line 2', side: 'deck', badge: 'REEF2', color: '#E08600', group: 'reef' },
  outhaul: { name: 'Outhaul', side: 'deck', badge: 'OUTH', color: '#D1A76E', group: 'main' },
};

export const DEFAULT_ROPE_CONFIG = {
  mainsheet: { max_working_load_n: 2500, default_trim: 0.65, max_length_m: 14.0 },
  boom_vang: { max_working_load_n: 2200, default_trim: 0.40, max_length_m: 6.0 },
  main_halyard: { max_working_load_n: 3500, default_trim: 0.95, max_length_m: 22.0 },
  jib_sheet_port: { max_working_load_n: 2500, default_trim: 0.60, max_length_m: 16.0 },
  jib_sheet_starboard: { max_working_load_n: 2500, default_trim: 0.60, max_length_m: 16.0 },
  furling_line: { max_working_load_n: 1800, default_trim: 0.05, max_length_m: 20.0 },
  cunningham: { max_working_load_n: 1800, default_trim: 0.30, max_length_m: 4.0 },
  outhaul: { max_working_load_n: 2000, default_trim: 0.70, max_length_m: 5.0 },
  reef_line_1: { max_working_load_n: 2500, default_trim: 0.05, max_length_m: 12.0 },
  reef_line_2: { max_working_load_n: 2500, default_trim: 0.05, max_length_m: 15.0 },
};

export class CockpitController {
  constructor(containerElement, apiBaseUrl = '') {
    this.container = typeof containerElement === 'string' ? document.getElementById(containerElement) : containerElement;
    this.apiBaseUrl = apiBaseUrl;
    this.state = null;
    this.awa_deg = 40.0;
    this.aws_kt = 15.0;
    this.heel_deg = 0.0;
    this.activePreset = 'FULL_SAIL';

    // Steering wheel & Rudder dynamics
    this.turns_to_max_rudder = 1.0;
    this.max_rudder_deg = 35.0;
    this.wheel_angle_deg = 0.0;
    this.rudder_actual_deg = 0.0;
    this.rudder_cmd_deg = 0.0;
    this.hydro_loss = 0.0;
    this.isDraggingWheel = false;
    this.wheelAnimFrame = null;
    this.draggingRopeId = null;
    this.controlMode = 'autopilot'; // 'autopilot' | 'skipper'

    // Initialize decoupled rope states
    this.ropeStates = {};
    Object.entries(DEFAULT_ROPE_CONFIG).forEach(([ropeId, cfg]) => {
      this.ropeStates[ropeId] = {
        rope_id: ropeId,
        actual_trim: cfg.default_trim,
        target_trim: cfg.default_trim,
        length_m: cfg.default_trim * cfg.max_length_m,
        max_length_m: cfg.max_length_m,
        tension_n: 200.0,
        max_working_load_n: cfg.max_working_load_n,
        status: 'OK',
        clamped: true,
        is_broken: false,
      };
    });

    if (this.container) {
      this.render();
      this.bindEvents();
      this.computeAllRopeTensions();
      this.updateAllRopesVisuals();
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="cockpit-container">
        <div class="cockpit-header">
          <div class="cockpit-title">
            <span>⚙ COCKPIT & RIG CONTROL</span>
            <div id="cockpit-mode-container" class="cockpit-mode-badge-wrap">
              <button id="btn-cockpit-mode-toggle" class="cockpit-mode-btn mode-autopilot" title="Режим: АВТОПИЛОТ. Троньте любой инструмент для перехода на ручное управление шкипера">
                <span id="cockpit-mode-icon">🤖</span>
                <span id="cockpit-mode-text">АВТОПИЛОТ (СЦЕНАРИЙ)</span>
              </button>
            </div>
          </div>
          <div class="cockpit-wind-summary" id="cockpit-wind-summary">
            <span>AWA: <b id="cockpit-awa">040°</b></span>
            <span>AWS: <b id="cockpit-aws">15.0 kt</b></span>
            <span>TACK: <b id="cockpit-tack" style="color:#34C759">STARBOARD</b></span>
          </div>
        </div>

        <!-- 3-Column Cockpit Grid (Port 25% | Center 50% | Starboard 25%) -->
        <div class="cockpit-grid">
          <!-- Port Column (25%) -->
          <div class="cockpit-col col-port">
            <div class="col-header">
              <span>PORTSIDE/LEFT</span>
              <span id="jib-status-badge" class="rope-status-badge status-ok">JIB: OK</span>
            </div>
            <div id="rope-jib_sheet_port"></div>
            <div id="rope-furling_line"></div>
            <div id="rope-cunningham"></div>
          </div>

          <!-- Center Column (50%) -->
          <div class="cockpit-col col-center">
            <div class="col-header">
              <span>CENTER (ДП / ШТУРВАЛ)</span>
              <span id="cockpit-helm-header-val" style="font-size:9px; color:#8b949e">HELM: 0.0° (0.00 об)</span>
            </div>
            
            <!-- HELM & RUDDER CONSOLE -->
            <div class="helm-rudder-widget">
              <div class="helm-title-row">
                <div class="rope-title-row">
                  <span class="rope-badge" style="background:#58a6ff; color:#fff">HELM</span>
                  <span style="font-size:11px; font-weight:700">Штурвал и Аксиометр</span>
                </div>
                <span id="rudder-hydro-badge" class="rope-status-badge status-ok">HYDRO: 100%</span>
              </div>

              <!-- Big Rotary Steering Wheel (186px SVG) -->
              <div class="helm-large-wheel-container">
                <div class="wheel-svg-wrapper-large" id="helm-wheel-svg-wrapper" title="Крутите штурвал мышкой (Drag / Scroll) • 2x клик = ДП">
                  <svg class="helm-wheel-svg-large" id="helmWheelSvg" viewBox="0 0 200 200" width="186" height="186">
                    <defs>
                      <filter id="wheel-shadow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#000" flood-opacity="0.6"/>
                      </filter>
                      <radialGradient id="hub-grad" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#2d333b"/>
                        <stop offset="100%" stop-color="#161b22"/>
                      </radialGradient>
                    </defs>

                    <!-- Outer Teak / Stainless Marine Rim -->
                    <circle cx="100" cy="100" r="88" fill="none" stroke="#262c36" stroke-width="12" filter="url(#wheel-shadow)" />
                    <!-- Metallic Grip Texture / Accents -->
                    <circle cx="100" cy="100" r="88" fill="none" stroke="#58a6ff" stroke-width="2" stroke-dasharray="4 26" opacity="0.9" />
                    <circle cx="100" cy="100" r="78" fill="none" stroke="#1c2128" stroke-width="3" />
                    <circle cx="100" cy="100" r="94" fill="none" stroke="#38414e" stroke-width="1.5" />

                    <!-- King Spoke Marker (Top Center Ribbon at 0°) -->
                    <rect x="96" y="4" width="8" height="18" rx="2.5" fill="#ff3b30" stroke="#b91c1c" stroke-width="1" />

                    <!-- 6 Marine Spokes -->
                    <line x1="100" y1="100" x2="100" y2="14" stroke="#8b949e" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="100" y1="100" x2="100" y2="186" stroke="#8b949e" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="100" y1="100" x2="26" y2="57" stroke="#8b949e" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="100" y1="100" x2="174" y2="143" stroke="#8b949e" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="100" y1="100" x2="26" y2="143" stroke="#8b949e" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="100" y1="100" x2="174" y2="57" stroke="#8b949e" stroke-width="4.5" stroke-linecap="round" />

                    <!-- Inner Stainless Flange Rings -->
                    <circle cx="100" cy="100" r="42" fill="none" stroke="#30363d" stroke-width="2" />
                    <circle cx="100" cy="100" r="32" fill="none" stroke="#484f58" stroke-width="1.5" stroke-dasharray="6 6" />

                    <!-- Center Marine Hub -->
                    <circle cx="100" cy="100" r="26" fill="url(#hub-grad)" stroke="#58a6ff" stroke-width="2.5" />
                    <circle cx="100" cy="100" r="14" fill="#0d1117" stroke="#30363d" stroke-width="1.5" />
                    <circle cx="100" cy="100" r="5" fill="#58a6ff" />
                  </svg>

                  <!-- Center Overlay Hub Button (Click to Center) -->
                  <div class="wheel-center-hud" id="helm-center-reset-btn" title="Кликните в центр для установки в 0° ДП">
                    <span class="hud-turns" id="helm-turns-display">0.00 об</span>
                    <span class="hud-angle" id="helm-angle-display">0.0° CTR</span>
                    <span class="hud-reset-badge">0° CTR</span>
                  </div>
                </div>
                
                <div class="wheel-hint-text">
                  <span>Крутите мышкой (Drag / Scroll) • Клик в центр / 2x клик = 0° ДП</span>
                </div>
              </div>

              <!-- Rudder Axiometer -->
              <div class="rudder-axiometer-card">
                <div class="axiometer-header">
                  <span>ИНДИКАТОР ПЕРА РУЛЯ (AXIOMETER)</span>
                  <div class="axiometer-readouts">
                    <span class="readout-actual">ACT: <b id="rudder-actual-val">0.0° CTR</b></span>
                    <span class="readout-cmd">CMD: <b id="rudder-cmd-val">0.0°</b></span>
                  </div>
                </div>
                
                <div class="axiometer-scale-track">
                  <div class="axiometer-center-mark"></div>
                  <div class="axiometer-pointer pointer-actual" id="axiometer-actual-pointer" style="left: 50%;"></div>
                  <div class="axiometer-pointer pointer-cmd" id="axiometer-cmd-pointer" style="left: 50%;"></div>
                </div>
                
                <div class="axiometer-ticks">
                  <span>PORT 35°</span>
                  <span>20°</span>
                  <span class="tick-center">0° ДП</span>
                  <span>20°</span>
                  <span>STBD 35°</span>
                </div>
              </div>
            </div>

            <!-- Reefing Scenarios Widget -->
            <div class="reefing-scenario-widget">
              <div class="preset-header">
                <span>⚡ РИФЛЕНИЕ И ПАРУСНЫЕ ПРЕСЕТЫ</span>
                <span id="reef-status-text" class="preset-status-text">FULL SAIL (100%)</span>
              </div>
              <div class="preset-buttons-grid">
                <button class="preset-btn active" data-preset="FULL_SAIL">FULL (100%)</button>
                <button class="preset-btn" data-preset="REEF_1">REEF 1 (75%)</button>
                <button class="preset-btn" data-preset="REEF_2">REEF 2 (50%)</button>
              </div>
              <div id="interlock-alert-box" class="interlock-alert"></div>
            </div>
          </div>

          <!-- Starboard Column (25%) -->
          <div class="cockpit-col col-starboard">
            <div class="col-header">
              <span>STARBOARD/RIGHT</span>
              <span id="main-status-badge" class="rope-status-badge status-ok">MAIN: OK</span>
            </div>
            <div id="rope-mainsheet"></div>
            <div id="rope-boom_vang"></div>
            <div id="rope-jib_sheet_starboard"></div>
          </div>
        </div>

        <!-- Tier 2: Traveler / Погон гика (100% Width) -->
        <div class="traveler-widget-full">
          <div class="rope-widget-top">
            <div class="rope-title-row">
              <span class="rope-badge" style="background:#58a6ff; color:#fff">TRAV</span>
              <span style="font-weight:700">Погон гика (Mainsheet Traveler)</span>
            </div>
            <span id="traveler-val-readout" class="traveler-pos-text"><b>0% (CENTER)</b></span>
          </div>
          <div class="traveler-track-container">
            <input type="range" id="traveler-slider" class="traveler-range-slider" min="-100" max="100" value="0" step="1" title="Погон гика: влево (Port) / вправо (Starboard)">
            <div class="traveler-ticks">
              <span>PORT -100%</span>
              <span class="tick-center">0% (ДП)</span>
              <span>STBD +100%</span>
            </div>
          </div>
          <div class="rope-controls-row">
            <button class="clutch-btn clamped" id="traveler-clutch-btn">🔒 BRAKE</button>
            <div class="step-btns">
              <button class="step-btn" id="traveler-btn-center">CTR 0%</button>
            </div>
          </div>
        </div>

        <!-- Tier 3: Lower Rig Deck (4 x 25% Grid) -->
        <div class="cockpit-deck-grid">
          <div id="rope-main_halyard"></div>
          <div id="rope-reef_line_1"></div>
          <div id="rope-reef_line_2"></div>
          <div id="rope-outhaul"></div>
        </div>
      </div>
    `;

    // Render individual rope widget cards
    Object.keys(ROPE_METADATA).forEach(ropeId => {
      const el = document.getElementById(`rope-${ropeId}`);
      if (el) {
        el.innerHTML = this.renderRopeWidgetHtml(ropeId, ROPE_METADATA[ropeId]);
      }
    });
  }

  renderRopeWidgetHtml(ropeId, meta) {
    return `
      <div class="rope-widget" id="widget-${ropeId}">
        <div class="rope-stripe" style="background: ${meta.color};"></div>
        
        <div class="rope-widget-top">
          <div class="rope-title-row">
            <span class="rope-badge">${meta.badge}</span>
            <span style="font-size:10px;">${meta.name}</span>
          </div>
          <span class="rope-status-badge status-ok" id="${ropeId}-status-badge">OK</span>
        </div>

        <div class="bars-container">
          <!-- Trim Bar (Interactive Drag & Wheel) -->
          <div class="bar-row">
            <div class="bar-label-row">
              <span>TRIM</span>
              <span id="${ropeId}-trim-val">50% (5.0m)</span>
            </div>
            <div class="bar-track trim-track" id="${ropeId}-trim-track" title="Тяните мышкой или крутите колесо мыши для натяжения">
              <div class="bar-fill-trim" id="${ropeId}-trim-fill" style="width: 50%;"></div>
              <div class="target-marker" id="${ropeId}-target-marker" style="left: 50%;"></div>
            </div>
          </div>

          <!-- Load Bar -->
          <div class="bar-row">
            <div class="bar-label-row">
              <span>LOAD</span>
              <span id="${ropeId}-load-val">200 N / SWL 2500 N</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill-load" id="${ropeId}-load-fill" style="width: 10%; background: var(--load-green);"></div>
            </div>
          </div>
        </div>

        <div class="rope-controls-row">
          <button class="clutch-btn clamped" id="${ropeId}-clutch-btn" data-rope="${ropeId}">
            🔒 CLAMPED
          </button>
          <div class="step-btns">
            <button class="step-btn" data-action="ease" data-rope="${ropeId}">-5%</button>
            <button class="step-btn" data-action="trim" data-rope="${ropeId}">+5%</button>
          </div>
        </div>
      </div>
    `;
  }

  setControlMode(mode, triggerSource = '') {
    if (this.controlMode === mode) return;
    this.controlMode = mode;

    const btn = document.getElementById('btn-cockpit-mode-toggle');
    const icon = document.getElementById('cockpit-mode-icon');
    const text = document.getElementById('cockpit-mode-text');

    if (mode === 'skipper') {
      if (btn) {
        btn.className = 'cockpit-mode-btn mode-skipper';
        btn.title = 'Режим: ШКИПЕР (Ручное управление). Кликните для возврата на автопилот сценария';
      }
      if (icon) icon.textContent = '🕹';
      if (text) text.textContent = 'ШКИПЕР (РУЧНОЕ) • НАЖМИТЕ ДЛЯ СБРОСА';
      if (window.Logger && triggerSource) {
        window.Logger.log('COCKPIT', 'WARN', `Шкипер взял управление в свои руки (${triggerSource}) -> SKIPPER MODE.`);
      }
    } else {
      if (btn) {
        btn.className = 'cockpit-mode-btn mode-autopilot';
        btn.title = 'Режим: АВТОПИЛОТ (Сценарий). Троньте любой инструмент для перехода на ручное управление';
      }
      if (icon) icon.textContent = '🤖';
      if (text) text.textContent = 'АВТОПИЛОТ (СЦЕНАРИЙ)';
      if (window.Logger) {
        window.Logger.log('COCKPIT', 'INFO', 'Возврат на автопилот симуляции (AUTOPILOT MODE).');
      }
    }
  }

  bindEvents() {
    // Mode Switcher Button
    const modeBtn = document.getElementById('btn-cockpit-mode-toggle');
    if (modeBtn) {
      modeBtn.addEventListener('click', () => {
        if (this.controlMode === 'skipper') {
          this.setControlMode('autopilot', 'Кнопка переключателя');
        } else {
          this.setControlMode('skipper', 'Кнопка переключателя');
        }
      });
    }

    // Preset Buttons
    this.container.querySelectorAll('.preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.setControlMode('skipper', `Пресет ${btn.dataset.preset}`);
        const preset = btn.dataset.preset;
        if (preset) this.sendPreset(preset);
      });
    });

    // Clutch Toggle Buttons
    this.container.querySelectorAll('.clutch-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.setControlMode('skipper', 'Стопор каната');
        const ropeId = btn.dataset.rope;
        if (ropeId && this.ropeStates[ropeId]) {
          const newClamped = !this.ropeStates[ropeId].clamped;
          this.ropeStates[ropeId].clamped = newClamped;
          this.computeRopeTension(ropeId);
          this.updateSingleRopeVisual(ropeId);
          this.sendRopeControl(ropeId, this.ropeStates[ropeId].actual_trim, newClamped);
        } else if (btn.id === 'traveler-clutch-btn') {
          const isClamped = btn.classList.contains('clamped');
          const newClamped = !isClamped;
          const slider = document.getElementById('traveler-slider');
          const pos = slider ? parseFloat(slider.value) / 100.0 : 0.0;
          btn.classList.toggle('clamped', newClamped);
          btn.textContent = newClamped ? '🔒 BRAKE' : '🔓 FREE';
          this.sendTravelerControl(pos, newClamped);
        }
      });
    });

    // Step +/- buttons (Isolated to target rope)
    this.container.querySelectorAll('.step-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const ropeId = btn.dataset.rope;
        if (!ropeId || !this.ropeStates[ropeId]) return;

        this.setControlMode('skipper', `Шаг натяжки ${ropeId}`);
        const action = btn.dataset.action;
        const rope = this.ropeStates[ropeId];
        const step = action === 'trim' ? 0.05 : -0.05;
        const newTrim = Math.max(0.0, Math.min(1.0, Math.round((rope.actual_trim + step) * 100) / 100));

        rope.actual_trim = newTrim;
        rope.target_trim = newTrim;
        rope.clamped = false; // Auto unclamp when stepping
        rope.length_m = newTrim * rope.max_length_m;

        this.computeRopeTension(ropeId);
        this.updateSingleRopeVisual(ropeId);
        this.sendRopeControl(ropeId, newTrim, false);
      });
    });

    // Interactive Mouse/Pointer Dragging & Wheel on All Rope Tracks (ISOLATED)
    Object.keys(ROPE_METADATA).forEach(ropeId => {
      const trimTrack = document.getElementById(`${ropeId}-trim-track`);
      const widget = document.getElementById(`widget-${ropeId}`);

      if (trimTrack) {
        let isDraggingTrack = false;
        let lastSendTime = 0;

        const updateTrimFromPointer = (clientX, forceSend = false) => {
          const rect = trimTrack.getBoundingClientRect();
          const ratio = Math.max(0.0, Math.min(1.0, (clientX - rect.left) / rect.width));
          const cleanTrim = Math.round(ratio * 100) / 100;

          const r = this.ropeStates[ropeId];
          if (r) {
            r.actual_trim = cleanTrim;
            r.target_trim = cleanTrim;
            r.length_m = cleanTrim * r.max_length_m;
            this.computeRopeTension(ropeId);
            this.updateSingleRopeVisual(ropeId);
          }

          const now = performance.now();
          if (forceSend || now - lastSendTime > 50) {
            lastSendTime = now;
            this.sendRopeControl(ropeId, cleanTrim, false);
          }
        };

        trimTrack.addEventListener('pointerdown', (e) => {
          this.setControlMode('skipper', `Канат ${ropeId}`);
          isDraggingTrack = true;
          this.draggingRopeId = ropeId;
          trimTrack.classList.add('dragging');
          trimTrack.setPointerCapture(e.pointerId);
          updateTrimFromPointer(e.clientX, true);
        });

        trimTrack.addEventListener('pointermove', (e) => {
          if (!isDraggingTrack) return;
          updateTrimFromPointer(e.clientX, false);
        });

        const stopTrackDrag = (e) => {
          if (isDraggingTrack) {
            isDraggingTrack = false;
            this.draggingRopeId = null;
            trimTrack.classList.remove('dragging');
            try {
              trimTrack.releasePointerCapture(e.pointerId);
            } catch (_) {}
            updateTrimFromPointer(e.clientX, true);
          }
        };

        trimTrack.addEventListener('pointerup', stopTrackDrag);
        trimTrack.addEventListener('pointercancel', stopTrackDrag);
      }

      // Mouse Wheel Support on Rope Widget (ISOLATED to this ropeId)
      if (widget) {
        widget.addEventListener('wheel', (e) => {
          e.preventDefault();
          this.setControlMode('skipper', `Колесо мыши ${ropeId}`);
          const r = this.ropeStates[ropeId];
          if (!r) return;

          const step = e.deltaY < 0 ? 0.05 : -0.05;
          const newTrim = Math.max(0.0, Math.min(1.0, Math.round((r.actual_trim + step) * 100) / 100));

          r.actual_trim = newTrim;
          r.target_trim = newTrim;
          r.length_m = newTrim * r.max_length_m;

          this.computeRopeTension(ropeId);
          this.updateSingleRopeVisual(ropeId);
          this.sendRopeControl(ropeId, newTrim, false);
        }, { passive: false });
      }
    });

    // Traveler Slider & Center Button
    const travelerSlider = document.getElementById('traveler-slider');
    const travelerBtnCenter = document.getElementById('traveler-btn-center');
    if (travelerSlider) {
      travelerSlider.addEventListener('input', (e) => {
        this.setControlMode('skipper', 'Погон гика (Traveler)');
        const val = parseFloat(e.target.value);
        const readout = document.getElementById('traveler-val-readout');
        if (readout) {
          const signStr = val < 0 ? `PORT (${val}%)` : (val > 0 ? `STBD (+${val}%)` : `0% (CENTER)`);
          readout.innerHTML = `<b>${signStr}</b>`;
        }
      });

      travelerSlider.addEventListener('change', (e) => {
        this.setControlMode('skipper', 'Погон гика (Traveler)');
        const val = parseFloat(e.target.value) / 100.0;
        this.sendTravelerControl(val, false);
      });
    }

    if (travelerBtnCenter) {
      travelerBtnCenter.addEventListener('click', () => {
        this.setControlMode('skipper', 'Погон гика в 0%');
        if (travelerSlider) travelerSlider.value = '0';
        const readout = document.getElementById('traveler-val-readout');
        if (readout) readout.innerHTML = '<b>0% (CENTER)</b>';
        this.sendTravelerControl(0.0, false);
      });
    }

    // Steering Wheel Rotary Mouse Drag & Center HUD Interactions
    const wheelWrap = document.getElementById('helm-wheel-svg-wrapper');
    const centerResetBtn = document.getElementById('helm-center-reset-btn');

    if (wheelWrap) {
      let startPointerAngle = 0;
      let startWheelAngle = 0;

      const getAngleFromCenter = (clientX, clientY) => {
        const rect = wheelWrap.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        return Math.atan2(clientY - centerY, clientX - centerX) * (180 / Math.PI);
      };

      wheelWrap.addEventListener('pointerdown', (e) => {
        if (e.target.closest('#helm-center-reset-btn')) return;
        if (this.wheelAnimFrame) cancelAnimationFrame(this.wheelAnimFrame);

        this.setControlMode('skipper', 'Штурвал');
        this.isDraggingWheel = true;
        wheelWrap.classList.add('dragging');
        wheelWrap.setPointerCapture(e.pointerId);

        startPointerAngle = getAngleFromCenter(e.clientX, e.clientY);
        startWheelAngle = this.wheel_angle_deg;
      });

      wheelWrap.addEventListener('pointermove', (e) => {
        if (!this.isDraggingWheel) return;
        const currentAngle = getAngleFromCenter(e.clientX, e.clientY);
        let delta = currentAngle - startPointerAngle;

        while (delta > 180) delta -= 360;
        while (delta < -180) delta += 360;

        const maxWheelDeg = this.turns_to_max_rudder * 360.0;
        this.wheel_angle_deg = Math.max(-maxWheelDeg, Math.min(maxWheelDeg, startWheelAngle + delta));
        this.rudder_actual_deg = (this.wheel_angle_deg / maxWheelDeg) * this.max_rudder_deg;

        this.updateHelmVisuals();
      });

      const stopWheelDrag = (e) => {
        if (this.isDraggingWheel) {
          this.isDraggingWheel = false;
          wheelWrap.classList.remove('dragging');
          try {
            wheelWrap.releasePointerCapture(e.pointerId);
          } catch (_) {}
        }
      };

      wheelWrap.addEventListener('pointerup', stopWheelDrag);
      wheelWrap.addEventListener('pointercancel', stopWheelDrag);

      wheelWrap.addEventListener('wheel', (e) => {
        e.preventDefault();
        if (this.wheelAnimFrame) cancelAnimationFrame(this.wheelAnimFrame);
        this.setControlMode('skipper', 'Колесо мыши на штурвале');

        const step = e.deltaY < 0 ? 12.0 : -12.0;
        const maxWheelDeg = this.turns_to_max_rudder * 360.0;
        this.wheel_angle_deg = Math.max(-maxWheelDeg, Math.min(maxWheelDeg, this.wheel_angle_deg + step));
        this.rudder_actual_deg = (this.wheel_angle_deg / maxWheelDeg) * this.max_rudder_deg;

        this.updateHelmVisuals();
      }, { passive: false });

      wheelWrap.addEventListener('dblclick', (e) => {
        e.preventDefault();
        this.setControlMode('skipper', '2x клик штурвала в 0°');
        this.smoothAnimateWheelTo(0.0);
      });
    }

    if (centerResetBtn) {
      centerResetBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.setControlMode('skipper', 'Клик центра штурвала в 0°');
        this.smoothAnimateWheelTo(0.0);
      });
    }
  }

  smoothAnimateWheelTo(targetAngleDeg, durationMs = 350) {
    if (this.wheelAnimFrame) cancelAnimationFrame(this.wheelAnimFrame);

    const startAngle = this.wheel_angle_deg;
    const diff = targetAngleDeg - startAngle;
    if (Math.abs(diff) < 0.1) {
      this.wheel_angle_deg = targetAngleDeg;
      this.rudder_actual_deg = (targetAngleDeg / (this.turns_to_max_rudder * 360.0)) * this.max_rudder_deg;
      this.updateHelmVisuals();
      return;
    }

    const startTime = performance.now();
    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(1.0, elapsed / durationMs);
      const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic

      this.wheel_angle_deg = startAngle + diff * ease;
      this.rudder_actual_deg = (this.wheel_angle_deg / (this.turns_to_max_rudder * 360.0)) * this.max_rudder_deg;
      this.updateHelmVisuals();

      if (progress < 1.0) {
        this.wheelAnimFrame = requestAnimationFrame(animate);
      } else {
        this.wheel_angle_deg = targetAngleDeg;
        this.rudder_actual_deg = (targetAngleDeg / (this.turns_to_max_rudder * 360.0)) * this.max_rudder_deg;
        this.updateHelmVisuals();
        this.wheelAnimFrame = null;
      }
    };
    this.wheelAnimFrame = requestAnimationFrame(animate);
  }

  updateHelmVisuals() {
    const wheelSvg = document.getElementById('helmWheelSvg');
    const helmAngleDisplay = document.getElementById('helm-angle-display');
    const helmTurnsDisplay = document.getElementById('helm-turns-display');
    const helmHeader = document.getElementById('cockpit-helm-header-val');
    const rudderActualVal = document.getElementById('rudder-actual-val');
    const rudderCmdVal = document.getElementById('rudder-cmd-val');
    const actualPointer = document.getElementById('axiometer-actual-pointer');
    const cmdPointer = document.getElementById('axiometer-cmd-pointer');
    const hydroBadge = document.getElementById('rudder-hydro-badge');

    if (wheelSvg) {
      wheelSvg.style.transform = `rotate(${this.wheel_angle_deg.toFixed(1)}deg)`;
    }

    const turns = (this.wheel_angle_deg / 360.0);
    const dirStr = this.rudder_actual_deg < -0.1 ? 'PORT' : (this.rudder_actual_deg > 0.1 ? 'STBD' : 'CTR');

    if (helmTurnsDisplay) {
      helmTurnsDisplay.textContent = `${Math.abs(turns).toFixed(2)} об`;
    }
    if (helmAngleDisplay) {
      helmAngleDisplay.textContent = `${Math.abs(this.rudder_actual_deg).toFixed(1)}° ${dirStr}`;
    }
    if (helmHeader) {
      helmHeader.textContent = `HELM: ${(this.rudder_actual_deg >= 0 ? '+' : '')}${this.rudder_actual_deg.toFixed(1)}° (${Math.abs(turns).toFixed(2)} об)`;
    }

    if (rudderActualVal) {
      rudderActualVal.textContent = `${(this.rudder_actual_deg >= 0 ? '+' : '')}${this.rudder_actual_deg.toFixed(1)}° ${dirStr}`;
    }
    if (rudderCmdVal) {
      rudderCmdVal.textContent = `${(this.rudder_cmd_deg >= 0 ? '+' : '')}${this.rudder_cmd_deg.toFixed(1)}°`;
    }

    if (actualPointer) {
      const pct = Math.max(0, Math.min(100, ((this.rudder_actual_deg + this.max_rudder_deg) / (2 * this.max_rudder_deg)) * 100));
      actualPointer.style.left = `${pct}%`;
    }
    if (cmdPointer) {
      const pct = Math.max(0, Math.min(100, ((this.rudder_cmd_deg + this.max_rudder_deg) / (2 * this.max_rudder_deg)) * 100));
      cmdPointer.style.left = `${pct}%`;
    }

    if (hydroBadge) {
      if (this.hydro_loss > 0.4) {
        hydroBadge.textContent = `STALL ${Math.round(this.hydro_loss * 100)}%`;
        hydroBadge.className = 'rope-status-badge status-overload';
      } else if (this.hydro_loss > 0.1) {
        hydroBadge.textContent = `HYDRO LOSS ${Math.round(this.hydro_loss * 100)}%`;
        hydroBadge.className = 'rope-status-badge status-taut';
      } else {
        hydroBadge.textContent = 'HYDRO: 100%';
        hydroBadge.className = 'rope-status-badge status-ok';
      }
    }
  }

  /**
   * Evaluates aerodynamic tension (in Newtons) for a single specific rope in isolation.
   */
  computeRopeTension(ropeId) {
    const r = this.ropeStates[ropeId];
    if (!r) return;

    const aws_m_s = Math.max(0.5, (this.aws_kt ?? 15.0) * 0.514444);
    const dynPressure = 0.5 * 1.225 * (aws_m_s * aws_m_s); // N/m2

    const radAwa = Math.abs(this.awa_deg ?? 40.0) * (Math.PI / 180.0);
    const radHeel = Math.abs(this.heel_deg ?? 0.0) * (Math.PI / 180.0);
    const angleLiftFactor = Math.max(0.25, Math.sin(radAwa));
    const heelRelief = Math.max(0.4, Math.cos(radHeel));

    let mainArea = 52.0;
    if (this.activePreset === 'REEF_1') mainArea *= 0.75;
    else if (this.activePreset === 'REEF_2') mainArea *= 0.50;

    const furlerTrim = this.ropeStates.furling_line ? this.ropeStates.furling_line.actual_trim : 0.05;
    const jibArea = 48.0 * Math.max(0.0, 1.0 - furlerTrim);

    const isStarboardTack = (this.awa_deg ?? 0) >= 0;
    let tension = 20.0;

    switch (ropeId) {
      case 'mainsheet': {
        const baseForce = dynPressure * mainArea * 0.92 * angleLiftFactor * heelRelief;
        tension = baseForce * 0.85 * (0.3 + 0.7 * r.actual_trim);
        break;
      }
      case 'boom_vang': {
        const baseForce = dynPressure * mainArea * 0.92 * angleLiftFactor * heelRelief;
        const msTrim = this.ropeStates.mainsheet ? this.ropeStates.mainsheet.actual_trim : 0.65;
        const demand = (1.0 - msTrim * 0.4) * (Math.abs(this.awa_deg ?? 40.0) / 80.0);
        tension = baseForce * 0.40 * Math.max(0.2, demand) * (0.3 + 0.7 * r.actual_trim);
        break;
      }
      case 'main_halyard': {
        const baseForce = dynPressure * mainArea * 0.92 * angleLiftFactor;
        tension = 800.0 * r.actual_trim + baseForce * 0.45;
        break;
      }
      case 'jib_sheet_port': {
        if (isStarboardTack) {
          const baseForce = dynPressure * jibArea * 0.95 * angleLiftFactor * heelRelief;
          tension = baseForce * 0.90 * (0.3 + 0.7 * r.actual_trim);
        } else {
          tension = 25.0; // Slack idle on leeward
        }
        break;
      }
      case 'jib_sheet_starboard': {
        if (!isStarboardTack) {
          const baseForce = dynPressure * jibArea * 0.95 * angleLiftFactor * heelRelief;
          tension = baseForce * 0.90 * (0.3 + 0.7 * r.actual_trim);
        } else {
          tension = 25.0; // Slack idle
        }
        break;
      }
      case 'furling_line': {
        const baseForce = dynPressure * 48.0 * 0.95 * angleLiftFactor;
        tension = baseForce * 0.35 * r.actual_trim + 40.0;
        break;
      }
      case 'cunningham': {
        const baseForce = dynPressure * mainArea * 0.92 * angleLiftFactor;
        tension = baseForce * 0.20 * r.actual_trim + 50.0;
        break;
      }
      case 'outhaul': {
        const baseForce = dynPressure * mainArea * 0.92 * angleLiftFactor;
        tension = baseForce * 0.25 * r.actual_trim + 80.0;
        break;
      }
      case 'reef_line_1': {
        const baseForce = dynPressure * 52.0 * 0.92 * angleLiftFactor;
        tension = (this.activePreset === 'REEF_1' || this.activePreset === 'REEF_2') ? baseForce * 0.65 * r.actual_trim : 30.0;
        break;
      }
      case 'reef_line_2': {
        const baseForce = dynPressure * 52.0 * 0.92 * angleLiftFactor;
        tension = (this.activePreset === 'REEF_2') ? baseForce * 0.70 * r.actual_trim : 30.0;
        break;
      }
      default:
        tension = 100.0;
    }

    r.tension_n = Math.max(10.0, Math.round(tension));

    const loadRatio = r.tension_n / r.max_working_load_n;
    if (r.is_broken) {
      r.status = 'BROKEN';
    } else if (loadRatio > 1.0) {
      r.status = 'OVERLOAD';
    } else if (loadRatio > 0.85) {
      r.status = 'TAUT';
    } else if (r.tension_n < 50.0) {
      r.status = 'SLACK';
    } else {
      r.status = 'OK';
    }
  }

  computeAllRopeTensions() {
    Object.keys(this.ropeStates).forEach(ropeId => this.computeRopeTension(ropeId));
  }

  /**
   * Updates exactly ONE rope's visual DOM elements in O(1) time.
   */
  updateSingleRopeVisual(ropeId) {
    const rState = this.ropeStates[ropeId];
    if (!rState) return;

    const trimFill = document.getElementById(`${ropeId}-trim-fill`);
    const targetMarker = document.getElementById(`${ropeId}-target-marker`);
    const trimVal = document.getElementById(`${ropeId}-trim-val`);
    const loadFill = document.getElementById(`${ropeId}-load-fill`);
    const loadVal = document.getElementById(`${ropeId}-load-val`);
    const statusBadge = document.getElementById(`${ropeId}-status-badge`);
    const clutchBtn = document.getElementById(`${ropeId}-clutch-btn`);

    if (this.draggingRopeId !== ropeId) {
      if (trimFill) trimFill.style.width = `${Math.round(rState.actual_trim * 100)}%`;
      if (targetMarker) targetMarker.style.left = `${Math.round(rState.target_trim * 100)}%`;
      const lenM = rState.length_m || (rState.actual_trim * (DEFAULT_ROPE_CONFIG[ropeId]?.max_length_m || 10.0));
      if (trimVal) trimVal.textContent = `${Math.round(rState.actual_trim * 100)}% (${lenM.toFixed(1)}m)`;
    }

    const loadPct = rState.max_working_load_n > 0 ? (rState.tension_n / rState.max_working_load_n) * 100 : 0;
    if (loadFill) {
      loadFill.style.width = `${Math.min(100, Math.round(loadPct))}%`;
      if (loadPct > 100) {
        loadFill.style.backgroundColor = 'var(--load-overload)';
      } else if (loadPct > 85) {
        loadFill.style.backgroundColor = 'var(--load-red)';
      } else if (loadPct > 60) {
        loadFill.style.backgroundColor = 'var(--load-yellow)';
      } else {
        loadFill.style.backgroundColor = 'var(--load-green)';
      }
    }
    if (loadVal) {
      loadVal.textContent = `${Math.round(rState.tension_n)} N / SWL ${Math.round(rState.max_working_load_n)} N`;
    }

    if (statusBadge) {
      statusBadge.textContent = rState.status;
      statusBadge.className = `rope-status-badge status-${rState.status.toLowerCase()}`;
    }

    if (clutchBtn) {
      clutchBtn.classList.toggle('clamped', Boolean(rState.clamped));
      clutchBtn.textContent = rState.clamped ? '🔒 CLAMPED' : '🔓 EASED';
    }
  }

  updateAllRopesVisuals() {
    Object.keys(this.ropeStates).forEach(ropeId => this.updateSingleRopeVisual(ropeId));
  }

  async sendRopeControl(ropeId, targetTrim, clamped) {
    try {
      const payload = {
        timestamp_ms: Date.now(),
        controls: [{ rope_id: ropeId, target_trim: targetTrim, clamped: clamped }]
      };
      await fetch(`${this.apiBaseUrl}/api/v1/controls/rig`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (err) {
      console.warn('Rope control dispatch note:', err);
    }
  }

  async sendTravelerControl(targetPos, clamped) {
    try {
      const payload = {
        timestamp_ms: Date.now(),
        controls: [{ rope_id: 'traveler', target_pos: targetPos, clamped: clamped }]
      };
      await fetch(`${this.apiBaseUrl}/api/v1/controls/rig`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (err) {
      console.warn('Traveler control dispatch note:', err);
    }
  }

  async sendPreset(presetName) {
    const alertBox = document.getElementById('interlock-alert-box');
    if (alertBox) alertBox.style.display = 'none';

    try {
      this.activePreset = presetName;
      if (presetName === 'REEF_1') {
        if (this.ropeStates.reef_line_1) this.ropeStates.reef_line_1.actual_trim = 0.85;
        if (this.ropeStates.mainsheet) this.ropeStates.mainsheet.actual_trim = Math.max(0.4, this.ropeStates.mainsheet.actual_trim * 0.85);
      } else if (presetName === 'REEF_2') {
        if (this.ropeStates.reef_line_1) this.ropeStates.reef_line_1.actual_trim = 0.85;
        if (this.ropeStates.reef_line_2) this.ropeStates.reef_line_2.actual_trim = 0.90;
        if (this.ropeStates.mainsheet) this.ropeStates.mainsheet.actual_trim = Math.max(0.3, this.ropeStates.mainsheet.actual_trim * 0.70);
      } else if (presetName === 'FULL_SAIL') {
        if (this.ropeStates.reef_line_1) this.ropeStates.reef_line_1.actual_trim = 0.05;
        if (this.ropeStates.reef_line_2) this.ropeStates.reef_line_2.actual_trim = 0.05;
      }

      this.computeAllRopeTensions();
      this.updateAllRopesVisuals();

      const payload = { timestamp_ms: Date.now(), preset: presetName };
      const res = await fetch(`${this.apiBaseUrl}/api/v1/controls/preset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.status === 409) {
        if (alertBox) {
          alertBox.textContent = `⚠ ${data.message || 'Interlock Failed: Ease mainsheet before reefing'}`;
          alertBox.style.display = 'block';
        }
      } else if (res.ok) {
        this.container.querySelectorAll('.preset-btn').forEach(b => {
          b.classList.toggle('active', b.dataset.preset === presetName);
        });
        const reefText = document.getElementById('reef-status-text');
        if (reefText) {
          reefText.textContent = `${presetName.replace('_', ' ')} (${Math.round((data.expected_area_ratio || 1.0) * 100)}%)`;
        }
      }
    } catch (err) {
      console.warn('Preset dispatch note:', err);
    }
  }

  async fetchTelemetry() {
    try {
      const res = await fetch(`${this.apiBaseUrl}/api/v1/telemetry/rig`);
      if (res.ok) {
        const data = await res.json();
        this.update(data);
      }
    } catch (err) {
      // Offline fallback
    }
  }

  update(telemetry) {
    if (!telemetry) return;
    this.state = telemetry;

    // Helm and Rudder update
    if (telemetry.helm) {
      if (telemetry.helm.command_deg !== undefined && telemetry.helm.command_deg !== null) {
        this.rudder_cmd_deg = telemetry.helm.command_deg;
      }
      if (telemetry.helm.hydro_loss !== undefined && telemetry.helm.hydro_loss !== null) {
        this.hydro_loss = telemetry.helm.hydro_loss;
      }

      // ONLY overwrite rudder and wheel angle from scenario telemetry if in AUTOPILOT mode
      if (this.controlMode === 'autopilot') {
        if (telemetry.helm.rudder_deg !== undefined && telemetry.helm.rudder_deg !== null) {
          this.rudder_actual_deg = telemetry.helm.rudder_deg;
          if (!this.isDraggingWheel) {
            const maxWheelDeg = this.turns_to_max_rudder * 360.0;
            this.wheel_angle_deg = (this.rudder_actual_deg / this.max_rudder_deg) * maxWheelDeg;
          }
        }
      }
      this.updateHelmVisuals();
    }

    if (telemetry.vessel) {
      this.heel_deg = telemetry.vessel.heel_deg ?? this.heel_deg;
    }

    if (telemetry.wind) {
      this.awa_deg = telemetry.wind.awa_deg ?? this.awa_deg;
      this.aws_kt = telemetry.wind.aws_kt ?? this.aws_kt;
      
      const awaEl = document.getElementById('cockpit-awa');
      const awsEl = document.getElementById('cockpit-aws');
      const tackEl = document.getElementById('cockpit-tack');

      if (awaEl) awaEl.textContent = `${Math.abs(Math.round(this.awa_deg)).toString().padStart(3, '0')}°`;
      if (awsEl) awsEl.textContent = `${(this.aws_kt).toFixed(1)} kt`;
      if (tackEl) {
        const isStbd = this.awa_deg >= 0;
        tackEl.textContent = isStbd ? 'STARBOARD' : 'PORT';
        tackEl.style.color = isStbd ? '#34C759' : '#007AFF';
      }

      // Tack-aware jib sheet dimming: AWA > 0 -> Port is loaded, Starboard is idle
      const portJibWidget = document.getElementById('widget-jib_sheet_port');
      const stbdJibWidget = document.getElementById('widget-jib_sheet_starboard');
      if (portJibWidget && stbdJibWidget) {
        portJibWidget.classList.toggle('dimmed', this.awa_deg < 0);
        stbdJibWidget.classList.toggle('dimmed', this.awa_deg >= 0);
      }
    }

    // Dynamic rope physics update on wind/heel changes
    this.computeAllRopeTensions();
    this.updateAllRopesVisuals();

    // Update Traveler if received from telemetry in autopilot mode
    if (telemetry.traveler && this.controlMode === 'autopilot') {
      const tSlider = document.getElementById('traveler-slider');
      const tClutch = document.getElementById('traveler-clutch-btn');
      const tVal = document.getElementById('traveler-val-readout');

      if (tSlider && document.activeElement !== tSlider) {
        tSlider.value = Math.round(telemetry.traveler.actual_pos * 100);
      }
      if (tClutch) {
        tClutch.classList.toggle('clamped', Boolean(telemetry.traveler.clamped));
        tClutch.textContent = telemetry.traveler.clamped ? '🔒 BRAKE' : '🔓 FREE';
      }
      if (tVal) {
        const p = Math.round(telemetry.traveler.actual_pos * 100);
        const signStr = p < 0 ? `PORT (${p}%)` : (p > 0 ? `STBD (+${p}%)` : `0% (CENTER)`);
        tVal.innerHTML = `<b>${signStr}</b>`;
      }
    }

    // Update Sail statuses
    if (telemetry.sails) {
      const mainStatus = document.getElementById('main-status-badge');
      const jibStatus = document.getElementById('jib-status-badge');

      if (mainStatus && telemetry.sails.mainsail) {
        const s = telemetry.sails.mainsail.status;
        mainStatus.textContent = `MAIN: ${s}`;
        mainStatus.className = `rope-status-badge status-${s.toLowerCase()}`;
      }
      if (jibStatus && (telemetry.sails.headsail || telemetry.sails.jib)) {
        const jibS = (telemetry.sails.headsail || telemetry.sails.jib).status;
        jibStatus.textContent = `JIB: ${jibS}`;
        jibStatus.className = `rope-status-badge status-${jibS.toLowerCase()}`;
      }
    }
  }
}
