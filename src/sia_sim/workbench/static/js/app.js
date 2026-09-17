/**
 * SIA Simulation Workbench — Main Application Orchestrator
 */

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  bindControls();
  bindVesselControls();
  bindLivingSeaToggle();

  if (window.ModalsController) {
    window.ModalsController.bindCustomWorldControls();
    window.ModalsController.bindCustomVesselControls();
    window.ModalsController.bindModalControls();
  }

  await loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS);
  if (window.renderZeroState) {
    window.renderZeroState(); // Initial state: boat is stationary at zero
  }
}

const SAIL_RIG_CATALOG = {
  mainsail: {
    id: 'mainsail',
    name: '⛵ MAINSAIL',
    areaRatio: 0.50,
    cardClass: '',
    reefs: [
      { label: 'Full (100%)', ratio: 1.0, badge: '100% FULL' },
      { label: 'R1 (75%)', ratio: 0.75, badge: '75% REEF 1' },
      { label: 'R2 (50%)', ratio: 0.50, badge: '50% REEF 2' },
      { label: 'R3 (35%)', ratio: 0.35, badge: '35% REEF 3' },
    ],
    douseLabel: '✕ Douse',
  },
  genoa: {
    id: 'genoa',
    name: '⛵ GENOA / JIB',
    areaRatio: 0.50,
    cardClass: '',
    reefs: [
      { label: 'Full (100%)', ratio: 1.0, badge: '100% FULL' },
      { label: 'R1 (75%)', ratio: 0.75, badge: '75% REEF 1' },
      { label: 'R2 (50%)', ratio: 0.50, badge: '50% REEF 2' },
    ],
    douseLabel: '✕ Furl',
  },
  code_zero: {
    id: 'code_zero',
    name: '⚡ CODE 0',
    areaRatio: 0.65,
    cardClass: 'card-highlight-code0',
    reefs: [
      { label: 'Full (100%)', ratio: 1.0, badge: '100% FULL' },
      { label: 'Furl (50%)', ratio: 0.50, badge: '50% FURL' },
    ],
    douseLabel: '✕ Furl',
  },
  gennaker: {
    id: 'gennaker',
    name: '🎈 GENNAKER A2/A3',
    areaRatio: 0.80,
    cardClass: 'card-highlight-gennaker',
    reefs: [
      { label: 'Full (100%)', ratio: 1.0, badge: '100% FULL' },
      { label: 'Depower (50%)', ratio: 0.50, badge: '50% DEPOWER' },
    ],
    douseLabel: '✕ Douse',
  },
  storm_jib: {
    id: 'storm_jib',
    name: '⛈ STORM JIB',
    areaRatio: 0.15,
    cardClass: 'card-highlight-storm',
    reefs: [
      { label: 'Full (100%)', ratio: 1.0, badge: '100% FULL' },
    ],
    douseLabel: '✕ Douse',
  },
};

function getAvailableSailsForCurrentVessel() {
  if (window.AppState.customVessel && window.AppState.customVessel.available_sails) {
    return window.AppState.customVessel.available_sails;
  }
  if (window.AppState.vesselPreset === 'monohull_ior') {
    return ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'storm_jib'];
  }
  return ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'code_zero', 'asymmetric_gennaker_a2', 'storm_jib'];
}

function updateVesselSpecsDisplay(vid) {
  const vspecLoa = document.getElementById('vspecLoa');
  const vspecBeam = document.getElementById('vspecBeam');
  const vspecMass = document.getElementById('vspecMass');
  const vspecArea = document.getElementById('vspecArea');

  const baseArea = window.AppState.customVessel?.sail_area_m2
    || (vid === 'beneteau_oceanis_45' ? 100.0 : 45.0);

  let totalEffectiveArea = 0.0;
  const activeSails = window.AppState.activeSails || {};
  Object.entries(activeSails).forEach(([k, ratio]) => {
    const sKey = k.toLowerCase().includes('main') ? 'mainsail'
      : k.toLowerCase().includes('code') ? 'code_zero'
      : k.toLowerCase().includes('genn') || k.toLowerCase().includes('para') ? 'gennaker'
      : k.toLowerCase().includes('storm') ? 'storm_jib'
      : 'genoa';
    const def = SAIL_RIG_CATALOG[sKey];
    if (def && ratio > 0) {
      totalEffectiveArea += baseArea * def.areaRatio * ratio;
    }
  });

  if (window.AppState.customVessel) {
    if (vspecLoa) vspecLoa.textContent = `${window.AppState.customVessel.loa_m.toFixed(2)} m`;
    if (vspecBeam) vspecBeam.textContent = `${window.AppState.customVessel.beam_m.toFixed(2)} m`;
    if (vspecMass) vspecMass.textContent = `${Math.round(window.AppState.customVessel.displacement_kg).toLocaleString()} kg`;
  } else if (vid === 'beneteau_oceanis_45') {
    if (vspecLoa) vspecLoa.textContent = '13.94 m';
    if (vspecBeam) vspecBeam.textContent = '4.50 m';
    if (vspecMass) vspecMass.textContent = '10,550 kg';
  } else {
    if (vspecLoa) vspecLoa.textContent = '10.50 m';
    if (vspecBeam) vspecBeam.textContent = '3.20 m';
    if (vspecMass) vspecMass.textContent = '4,500 kg';
  }

  if (vspecArea) {
    vspecArea.textContent = totalEffectiveArea === 0 ? '0 m² (Motor)' : `${totalEffectiveArea.toFixed(1)} m²`;
  }
}

function renderActiveSailsDeck() {
  const container = document.getElementById('activeSailsDeck');
  const vesselPlanTag = document.getElementById('vesselPlanTag');
  if (!container) return;

  const activeSails = window.AppState.activeSails || {};
  const activeKeys = Object.keys(activeSails).filter(k => activeSails[k] > 0);

  if (activeKeys.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 10px 14px; background: rgba(11, 19, 36, 0.6); border: 1px dashed rgba(59, 130, 246, 0.35); border-radius: 6px; text-align: center; color: var(--text-muted); font-size: 11px;">
        ⚙ <b>BARE POLES</b> — No sails hoisted (0% power). Boat is motoring or drifting. Click <b>+ Hoist Sail</b> or pick a preset below.
      </div>
    `;
    if (vesselPlanTag) vesselPlanTag.textContent = 'BARE POLES (0 m²)';
    updateVesselSpecsDisplay(window.AppState.vesselPreset);
    highlightPresetButton('BARE_POLES');
    return;
  }

  // Build card for each active sail
  const cardsHtml = activeKeys.map((k) => {
    const sKey = k.toLowerCase().includes('main') ? 'mainsail'
      : k.toLowerCase().includes('code') ? 'code_zero'
      : k.toLowerCase().includes('genn') || k.toLowerCase().includes('para') ? 'gennaker'
      : k.toLowerCase().includes('storm') ? 'storm_jib'
      : 'genoa';
    const def = SAIL_RIG_CATALOG[sKey] || SAIL_RIG_CATALOG.mainsail;
    const currentRatio = activeSails[k];

    const currentReef = def.reefs.find(r => Math.abs(r.ratio - currentRatio) < 0.05) || {
      badge: `${Math.round(currentRatio * 100)}% REEF`,
      ratio: currentRatio,
    };

    const reefButtonsHtml = def.reefs.map((r) => {
      const isSelected = Math.abs(r.ratio - currentRatio) < 0.05 ? ' active' : '';
      return `<button class="btn-reef${isSelected}" data-sail="${k}" data-ratio="${r.ratio}">${r.label}</button>`;
    }).join('');

    return `
      <div class="active-sail-card ${def.cardClass}">
        <div class="sail-card-header">
          <span class="sail-card-name">${def.name}</span>
          <span class="sail-card-badge">${currentReef.badge}</span>
        </div>
        <div class="sail-reef-btn-group">
          ${reefButtonsHtml}
          <button class="btn-reef btn-douse" data-sail="${k}" data-action="douse" title="Douse/furl this sail">${def.douseLabel}</button>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = cardsHtml;

  // Bind click listeners for reef buttons and douse
  container.querySelectorAll('.btn-reef').forEach((btn) => {
    btn.addEventListener('click', () => {
      const sailId = btn.getAttribute('data-sail');
      const action = btn.getAttribute('data-action');
      const ratio = parseFloat(btn.getAttribute('data-ratio'));

      if (action === 'douse') {
        delete window.AppState.activeSails[sailId];
      } else if (!isNaN(ratio)) {
        window.AppState.activeSails[sailId] = ratio;
      }

      renderActiveSailsDeck();
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
    loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents, true);
    });
  });

  // Summary tag
  const tagSummary = activeKeys.map((k) => {
    const sKey = k.toLowerCase().includes('main') ? 'MAIN'
      : k.toLowerCase().includes('code') ? 'CODE 0'
      : k.toLowerCase().includes('genn') ? 'GENNAKER'
      : k.toLowerCase().includes('storm') ? 'STORM JIB'
      : 'GENOA';
    const pct = Math.round((activeSails[k] || 1.0) * 100);
    return `${sKey} ${pct}%`;
  }).join(' + ');

  if (vesselPlanTag) {
    vesselPlanTag.textContent = tagSummary;
  }

  updateVesselSpecsDisplay(window.AppState.vesselPreset);
}

function highlightPresetButton(presetKey) {
  const strip = document.getElementById('sailPresetStrip');
  if (!strip) return;
  strip.querySelectorAll('.btn-preset-chip').forEach((btn) => {
    btn.classList.toggle('active', btn.getAttribute('data-preset') === presetKey);
  });
}

function bindSailPresetControls() {
  const strip = document.getElementById('sailPresetStrip');
  if (strip) {
    strip.querySelectorAll('.btn-preset-chip').forEach((btn) => {
      btn.addEventListener('click', () => {
        const preset = btn.getAttribute('data-preset');
        window.AppState.sailPlan = preset;

        if (preset === 'FULL_MAIN') {
          window.AppState.activeSails = { mainsail: 1.0, genoa: 1.0 };
        } else if (preset === 'CODE_ZERO') {
          window.AppState.activeSails = { mainsail: 1.0, code_zero: 1.0 };
        } else if (preset === 'GENNAKER') {
          window.AppState.activeSails = { mainsail: 1.0, gennaker: 1.0 };
        } else if (preset === 'REEF_1') {
          window.AppState.activeSails = { mainsail: 0.75, genoa: 0.85 };
        } else if (preset === 'REEF_2') {
          window.AppState.activeSails = { mainsail: 0.55, genoa: 0.65 };
        } else if (preset === 'STORM_JIB') {
          window.AppState.activeSails = { storm_jib: 1.0 };
        } else if (preset === 'BARE_POLES') {
          window.AppState.activeSails = {};
        }

        highlightPresetButton(preset);
        renderActiveSailsDeck();
        const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
        loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents, true);
      });
    });
  }

  // Hoist Sail button
  const btnHoist = document.getElementById('btnHoistSail');
  if (btnHoist) {
    btnHoist.addEventListener('click', () => {
      const avail = getAvailableSailsForCurrentVessel();
      const current = window.AppState.activeSails || {};

      // Determine unhoisted candidates
      const candidates = [];
      if (!current.mainsail && (avail.includes('mainsail_square_top') || avail.includes('mainsail'))) candidates.push({ id: 'mainsail', name: '⛵ Mainsail' });
      if (!current.genoa && (avail.includes('genoa_furling') || avail.includes('solent_jib') || avail.includes('genoa'))) candidates.push({ id: 'genoa', name: '⛵ Genoa / Jib' });
      if (!current.code_zero && avail.includes('code_zero')) candidates.push({ id: 'code_zero', name: '⚡ Code 0' });
      if (!current.gennaker && (avail.includes('asymmetric_gennaker_a2') || avail.includes('asymmetric_gennaker_a3') || avail.includes('parasailor'))) candidates.push({ id: 'gennaker', name: '🎈 Gennaker' });
      if (!current.storm_jib && avail.includes('storm_jib')) candidates.push({ id: 'storm_jib', name: '⛈ Storm Jib' });

      if (candidates.length === 0) {
        alert('All available sails from your wardrobe are currently hoisted!');
        return;
      }

      const promptText = `Select sail to hoist:\n` + candidates.map((c, i) => `${i + 1}. ${c.name}`).join('\n');
      const choice = prompt(promptText, '1');
      if (choice) {
        const idx = parseInt(choice, 10) - 1;
        if (candidates[idx]) {
          window.AppState.activeSails[candidates[idx].id] = 1.0;
          renderActiveSailsDeck();
          const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
          loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents, true);
        }
      }
    });
  }
}

window.renderActiveSailsDeck = renderActiveSailsDeck;
window.updateVesselSpecsDisplay = updateVesselSpecsDisplay;

function bindVesselControls() {
  const vesselSelect = document.getElementById('vesselSelect');

  if (vesselSelect) {
    vesselSelect.addEventListener('change', (e) => {
      window.AppState.vesselPreset = e.target.value;
      window.AppState.customVessel = null; // reset custom override when preset switches
      window.AppState.activeSails = { mainsail: 1.0, genoa: 1.0 };
      renderActiveSailsDeck();
      if (window.renderQueryActions) window.renderQueryActions();
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents, false);
    });
  }

  bindSailPresetControls();
  renderActiveSailsDeck();
  if (window.renderQueryActions) window.renderQueryActions();
}

function bindLivingSeaToggle() {
  const btn = document.getElementById('btnLivingSeaToggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (window.AppState.isPlaying) {
      if (window.pauseSimulation) window.pauseSimulation();
    } else {
      if (window.playSimulation) window.playSimulation();
    }
  });
}

function bindControls() {
  const btnRun = document.getElementById('btnRun');
  const btnPause = document.getElementById('btnPause');
  const btnStep = document.getElementById('btnStep');
  const btnReset = document.getElementById('btnReset');
  const scenarioSelect = document.getElementById('scenarioSelect');
  const imuRateSelect = document.getElementById('imuRateSelect');
  const dampingSelect = document.getElementById('dampingSelect');
  const durationSelect = document.getElementById('durationSelect');
  const seedInput = document.getElementById('seedInput');
  const btnModeLive = document.getElementById('btnModeLive');
  const btnModeDebug = document.getElementById('btnModeDebug');

  if (btnRun) btnRun.addEventListener('click', () => window.playSimulation && window.playSimulation());
  if (btnPause) btnPause.addEventListener('click', () => window.pauseSimulation && window.pauseSimulation());
  if (btnStep) {
    btnStep.addEventListener('click', () => {
      if (window.stepSimulation) window.stepSimulation(1);
    });
  }
  if (btnReset) {
    btnReset.addEventListener('click', () => window.stopLivingSeaToZero && window.stopLivingSeaToZero());
  }

  if (scenarioSelect) {
    scenarioSelect.addEventListener('change', (e) => {
      window.AppState.scenarioId = e.target.value;
      window.AppState.customWorld = null; // reset custom override on preset change
      const durVal = durationSelect ? (parseInt(durationSelect.value, 10) || 20) : 20;
      window.AppState.durationS = durVal;
      // Preserve any events placed by human, or keep timeline clean if empty
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : [];
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents, false);
    });
  }

  if (imuRateSelect) {
    imuRateSelect.addEventListener('change', (e) => {
      window.AppState.imuRate = parseInt(e.target.value, 10) || 100;
      loadScenario(
        window.AppState.scenarioId,
        window.AppState.seed,
        window.AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null,
        true
      );
    });
  }

  if (dampingSelect) {
    dampingSelect.addEventListener('change', (e) => {
      window.AppState.damping = e.target.value;
      if (window.InstrumentRenderer) {
        window.InstrumentRenderer.setDampingMode(window.AppState.damping);
      }
    });
  }

  if (durationSelect) {
    durationSelect.addEventListener('change', (e) => {
      window.AppState.durationS = parseInt(e.target.value, 10) || 20;
      loadScenario(
        window.AppState.scenarioId,
        window.AppState.seed,
        window.AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null,
        true
      );
    });
  }

  if (seedInput) {
    seedInput.addEventListener('change', (e) => {
      window.AppState.seed = parseInt(e.target.value, 10) || 42;
      loadScenario(
        window.AppState.scenarioId,
        window.AppState.seed,
        window.AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null,
        false
      );
    });
  }

  const speedSelect = document.getElementById('speedSelect');
  if (speedSelect) {
    speedSelect.addEventListener('change', (e) => {
      window.AppState.speedMultiplier = parseFloat(e.target.value) || 2.0;
      if (window.AppState.isPlaying) {
        window.pauseSimulation();
        window.playSimulation();
      }
    });
  }

  if (btnModeLive) btnModeLive.addEventListener('click', () => setMode('live'));
  if (btnModeDebug) btnModeDebug.addEventListener('click', () => setMode('debug'));

  // Timeline Zoom Buttons
  const btnZoomIn = document.getElementById('btnZoomIn');
  const btnZoomOut = document.getElementById('btnZoomOut');
  const btnZoomReset = document.getElementById('btnZoomReset');

  if (btnZoomIn) btnZoomIn.addEventListener('click', () => window.TimelineRenderer && window.TimelineRenderer.zoomIn());
  if (btnZoomOut) btnZoomOut.addEventListener('click', () => window.TimelineRenderer && window.TimelineRenderer.zoomOut());
  if (btnZoomReset) btnZoomReset.addEventListener('click', () => window.TimelineRenderer && window.TimelineRenderer.resetZoom());

  // Timeline Event Tool Palette
  const toolButtons = document.querySelectorAll('.btn-timeline-tool');
  toolButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const toolType = btn.getAttribute('data-tool');
      const isActive = btn.classList.contains('active');
      toolButtons.forEach(b => b.classList.remove('active'));

      if (!isActive && window.TimelineRenderer) {
        btn.classList.add('active');
        window.TimelineRenderer.setTool(toolType);
      } else if (window.TimelineRenderer) {
        window.TimelineRenderer.setTool(null);
      }
    });
  });

  const btnResetEvents = document.getElementById('btnResetEvents');
  if (btnResetEvents) {
    btnResetEvents.addEventListener('click', () => {
      // Restore default scenario/preset events from backend
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, null, true);
    });
  }

  const btnClearTimeline = document.getElementById('btnClearTimeline');
  if (btnClearTimeline) {
    btnClearTimeline.addEventListener('click', () => {
      if (window.TimelineRenderer) {
        window.TimelineRenderer.events = [];
        window.TimelineRenderer.renderTracks();
      }
      // Send explicit empty list of events so ship sails in pure living background
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, [], true);
    });
  }

  // Keyboard shortcuts (Space = Play/Pause, ArrowRight = Step)
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.code === 'Space') {
      e.preventDefault();
      window.AppState.isPlaying ? window.pauseSimulation() : window.playSimulation();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      window.stepSimulation(1);
    }
  });
}

function setMode(mode) {
  window.AppState.mode = mode;
  document.body.className = `mode-${mode}`;
  const btnLive = document.getElementById('btnModeLive');
  const btnDebug = document.getElementById('btnModeDebug');
  if (btnLive) btnLive.classList.toggle('active', mode === 'live');
  if (btnDebug) btnDebug.classList.toggle('active', mode === 'debug');
}

async function loadScenario(scenarioId, seed, durationS = 20, customEvents = null, preserveTime = true) {
  const wasPlaying = window.AppState ? window.AppState.isPlaying : false;
  const savedSimTimeMs = (preserveTime && window.AppState && window.AppState.currentSimTimeMs > 0)
    ? window.AppState.currentSimTimeMs
    : 0.0;

  if (window.pauseSimulation) window.pauseSimulation();
  window.userConfirmedSail = null;

  try {
    const payload = {
      scenario: scenarioId,
      vessel_preset: window.AppState.vesselPreset || 'beneteau_oceanis_45',
      sail_plan: window.AppState.sailPlan || 'FULL_MAIN',
      active_sails: window.AppState.activeSails || { mainsail: 1.0, genoa: 1.0 },
      seed: seed,
      duration_ms: durationS * 1000,
      imu_sample_rate_hz: window.AppState.imuRate,
    };
    if (customEvents !== null) {
      payload.events = customEvents;
    }
    if (window.AppState.customWorld) {
      payload.custom_world = window.AppState.customWorld;
    }
    if (window.AppState.customVessel) {
      payload.custom_vessel = window.AppState.customVessel;
    }

    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    if (json.error) {
      alert(`Simulation run failed: ${json.error}`);
      return;
    }
    window.AppState.data = json;
    window.AppState.currentSimTimeMs = savedSimTimeMs;
    window.userConfirmedSail = null;
    window.queryActiveUntilMs = 0;
    window.queryTriggeredAtMs = 0;
    
    if (window.TimelineRenderer) {
      window.TimelineRenderer.init(window.AppState.data, customEvents);
      window.TimelineRenderer.onEventsChanged = (updatedEvents) => {
        loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, updatedEvents, true);
      };
    }

    if (savedSimTimeMs === 0 && !window.AppState.isLivingSeaRunning) {
      if (window.renderZeroState) window.renderZeroState();
    } else {
      if (window.renderAtTime) window.renderAtTime(savedSimTimeMs);
    }

    if (window.Logger) {
      window.Logger.log(
        'PHYSICS',
        'INFO',
        `Сценарий пересчитан с новыми параметрами парусов (t=${(savedSimTimeMs / 1000).toFixed(2)}с)`,
        { sails: window.AppState.activeSails },
        savedSimTimeMs
      );
    }

    if (wasPlaying && window.playSimulation) {
      window.playSimulation();
    }
  } catch (err) {
    console.error('Failed to load scenario:', err);
  }
}

window.loadScenario = loadScenario;

