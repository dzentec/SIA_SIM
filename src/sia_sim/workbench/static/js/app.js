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
  bindInstrumentsViewToggle();

  if (window.ModalsController) {
    window.ModalsController.bindCustomWorldControls();
    window.ModalsController.bindCustomVesselControls();
    window.ModalsController.bindActiveSailPlanModalControls();
    window.ModalsController.bindModalControls();
  }

  await loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS);
  if (window.renderZeroState) {
    window.renderZeroState(); // Initial state: boat is stationary at zero
  }
}

function bindInstrumentsViewToggle() {
  const btn6Dial = document.getElementById('btnView6Dial');
  const btnSailSteer = document.getElementById('btnViewSailSteer');
  const track = document.getElementById('instrumentsSliderTrack');

  function setViewMode(mode) {
    window.AppState.instrumentsViewMode = mode;
    if (mode === 'sailsteer') {
      if (btn6Dial) btn6Dial.classList.remove('active');
      if (btnSailSteer) btnSailSteer.classList.add('active');
      if (track) {
        track.classList.remove('view-mode-6dial');
        track.classList.add('view-mode-sailsteer');
      }
      if (window.Logger) {
        window.Logger.log('PHYSICS', 'INFO', 'Режим приборов: B&G SailSteer™ Navigation Display (16:9).');
      }
    } else {
      if (btnSailSteer) btnSailSteer.classList.remove('active');
      if (btn6Dial) btn6Dial.classList.add('active');
      if (track) {
        track.classList.remove('view-mode-sailsteer');
        track.classList.add('view-mode-6dial');
      }
      if (window.Logger) {
        window.Logger.log('PHYSICS', 'INFO', 'Режим приборов: 6-Dial Marine Instrument Suite.');
      }
    }
  }

  if (btn6Dial) {
    btn6Dial.addEventListener('click', () => setViewMode('6dial'));
  }
  if (btnSailSteer) {
    btnSailSteer.addEventListener('click', () => setViewMode('sailsteer'));
  }

  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
    if (e.key === 's' || e.key === 'S') {
      const current = window.AppState.instrumentsViewMode || '6dial';
      setViewMode(current === '6dial' ? 'sailsteer' : '6dial');
    }
  });

  window.setInstrumentsViewMode = setViewMode;
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

const WARDROBE_DISPLAY_NAMES = {
  mainsail_square_top: 'MAINSAIL',
  genoa_furling: 'GENOA',
  solent_jib: 'SOLENT',
  code_zero: 'CODE 0',
  asymmetric_gennaker_a2: 'GENNAKER A2',
  asymmetric_gennaker_a3: 'GENNAKER A3',
  parasailor: 'PARASAILOR',
  storm_jib: 'STORM JIB',
};

function renderVesselWardrobe() {
  const container = document.getElementById('vesselWardrobeStrip');
  if (container) {
    const avail = getAvailableSailsForCurrentVessel();
    const slots = window.AppState.tackSlots || {};
    const activeList = [slots.main, slots.inner, slots.outer, slots.bowsprit].filter(Boolean);

    const tagsHtml = avail.map((id) => {
      const isHoisted = activeList.includes(id);
      const label = WARDROBE_DISPLAY_NAMES[id] || id.toUpperCase();
      const statusIcon = isHoisted ? '● ' : '○ ';
      return `<span class="wardrobe-tag${isHoisted ? ' active' : ''}" title="${id}">${statusIcon}${label}</span>`;
    }).join('');

    container.innerHTML = tagsHtml;
  }
  updateVesselSpecsDisplay(window.AppState.vesselPreset);
}

window.renderVesselWardrobe = renderVesselWardrobe;
window.renderActiveSailsDeck = renderVesselWardrobe; // Compatibility alias
window.updateVesselSpecsDisplay = updateVesselSpecsDisplay;

function bindVesselControls() {
  const vesselSelect = document.getElementById('vesselSelect');

  if (vesselSelect) {
    vesselSelect.addEventListener('change', (e) => {
      window.AppState.vesselPreset = e.target.value;
      window.AppState.customVessel = null; // reset custom override when preset switches
      window.AppState.tackSlots = { main: 'mainsail_square_top', inner: null, outer: 'genoa_furling', bowsprit: null };
      window.AppState.activeSails = { mainsail: 1.0, genoa: 1.0 };
      
      if (window.ModalsController && window.ModalsController.populateActiveSailPlanModal) {
        window.ModalsController.populateActiveSailPlanModal();
      }
      if (window.CockpitController && window.CockpitController.updateActiveSailPlanVisuals) {
        window.CockpitController.updateActiveSailPlanVisuals();
      }
      renderVesselWardrobe();
      if (window.renderQueryActions) window.renderQueryActions();
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents, false);
    });
  }

  renderVesselWardrobe();
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

