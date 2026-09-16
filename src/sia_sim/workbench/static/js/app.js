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

const ALL_SAIL_PLAN_DEFS = [
  {
    id: 'GENNAKER',
    name: '⛵ GENNAKER (150%)',
    powerPct: 150,
    reqSails: ['asymmetric_gennaker_a2', 'asymmetric_gennaker_a3'],
    cssClass: 'highlight-code0',
    title: 'Gennaker A2/A3 + Main (150% Power)'
  },
  {
    id: 'PARASAILOR',
    name: '🪁 PARASAILOR (140%)',
    powerPct: 140,
    reqSails: ['parasailor'],
    cssClass: 'highlight-code0',
    title: 'Winged Parasailor (140% Power)'
  },
  {
    id: 'CODE_ZERO',
    name: '⛵ CODE 0 (130%)',
    powerPct: 130,
    reqSails: ['code_zero'],
    cssClass: 'highlight-code0',
    title: 'Code Zero + Main (130% Power)'
  },
  {
    id: 'FULL_MAIN',
    name: '⛵ FULL MAIN (100%)',
    powerPct: 100,
    reqSails: ['mainsail_square_top'],
    cssClass: '',
    title: 'Full Main + Genoa/Jib (100% Power)'
  },
  {
    id: 'REEF_1',
    name: '📉 REEF 1 (75%)',
    powerPct: 75,
    reqSails: ['mainsail_square_top'],
    cssClass: '',
    title: 'Reef 1 Main (75% Power)'
  },
  {
    id: 'REEF_2',
    name: '📉 REEF 2 (50%)',
    powerPct: 50,
    reqSails: ['mainsail_square_top'],
    cssClass: '',
    title: 'Reef 2 Main (50% Power)'
  },
  {
    id: 'REEF_3',
    name: '📉 REEF 3 (35%)',
    powerPct: 35,
    reqSails: ['mainsail_square_top'],
    cssClass: '',
    title: 'Reef 3 Main (35% Power)'
  },
  {
    id: 'GENOA_ONLY',
    name: '⛵ GENOA (50%)',
    powerPct: 50,
    reqSails: ['genoa_furling'],
    cssClass: '',
    title: 'Furling Genoa Only (50% Power)'
  },
  {
    id: 'JIB_ONLY',
    name: '⛵ JIB (40%)',
    powerPct: 40,
    reqSails: ['solent_jib'],
    cssClass: '',
    title: 'Solent Jib Only (40% Power)'
  },
  {
    id: 'STORM_JIB',
    name: '⛈ STORM JIB (25%)',
    powerPct: 25,
    reqSails: ['storm_jib'],
    cssClass: '',
    title: 'Storm Jib (25% Power)'
  },
  {
    id: 'BARE_POLES',
    name: '⚙ BARE POLES (0%)',
    powerPct: 0,
    reqSails: [], // Always available
    cssClass: '',
    title: 'Bare Poles / Motoring (0% Power)'
  },
];

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
  const planDef = ALL_SAIL_PLAN_DEFS.find(p => p.id === window.AppState.sailPlan);
  const powerFactor = planDef ? (planDef.powerPct / 100.0) : 1.0;
  const effectiveArea = baseArea * powerFactor;

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
    vspecArea.textContent = effectiveArea === 0 ? '0 m² (Motor)' : `${effectiveArea.toFixed(0)} m²`;
  }
}

function updateSailChipsGrid(availableSails = null) {
  const sails = availableSails || getAvailableSailsForCurrentVessel();
  const container = document.getElementById('sailChipsGrid');
  const vesselPlanTag = document.getElementById('vesselPlanTag');
  if (!container) return;

  // Filter plans matching current available wardrobe
  const validPlans = ALL_SAIL_PLAN_DEFS.filter(plan => {
    if (!plan.reqSails || plan.reqSails.length === 0) return true;
    return plan.reqSails.some(s => sails.includes(s));
  });

  const validPlanIds = validPlans.map(p => p.id);
  if (!validPlanIds.includes(window.AppState.sailPlan)) {
    if (validPlanIds.includes('FULL_MAIN')) {
      window.AppState.sailPlan = 'FULL_MAIN';
    } else if (validPlanIds.length > 0) {
      window.AppState.sailPlan = validPlanIds[0];
    } else {
      window.AppState.sailPlan = 'BARE_POLES';
    }
  }

  // Render buttons
  container.innerHTML = validPlans.map(plan => {
    const isActive = plan.id === window.AppState.sailPlan ? 'active' : '';
    const extraClass = plan.cssClass ? ` ${plan.cssClass}` : '';
    return `<button class="btn-sail-chip ${isActive}${extraClass}" data-sail="${plan.id}" title="${plan.title}">${plan.name}</button>`;
  }).join('');

  // Update tag
  const activePlanDef = validPlans.find(p => p.id === window.AppState.sailPlan);
  if (vesselPlanTag && activePlanDef) {
    vesselPlanTag.textContent = activePlanDef.name.replace(/^[^\w\dа-яА-ЯёЁ]+/, '').trim();
  }

  // Bind click listeners
  const chips = container.querySelectorAll('.btn-sail-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const plan = chip.getAttribute('data-sail');
      window.AppState.sailPlan = plan;
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      if (vesselPlanTag) {
        vesselPlanTag.textContent = chip.textContent.trim();
      }
      updateVesselSpecsDisplay(window.AppState.vesselPreset);

      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents);
    });
  });

  updateVesselSpecsDisplay(window.AppState.vesselPreset);
}

window.updateSailChipsGrid = updateSailChipsGrid;
window.updateVesselSpecsDisplay = updateVesselSpecsDisplay;

function bindVesselControls() {
  const vesselSelect = document.getElementById('vesselSelect');

  if (vesselSelect) {
    vesselSelect.addEventListener('change', (e) => {
      window.AppState.vesselPreset = e.target.value;
      window.AppState.customVessel = null; // reset custom override when preset switches
      updateSailChipsGrid();
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents);
    });
  }

  updateSailChipsGrid();
}

function bindLivingSeaToggle() {
  const btn = document.getElementById('btnLivingSeaToggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (!window.AppState.isLivingSeaRunning) {
      if (window.startLivingSea) window.startLivingSea();
    } else {
      if (window.stopLivingSeaToZero) window.stopLivingSeaToZero();
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

  if (btnRun) btnRun.addEventListener('click', () => window.startLivingSea && window.startLivingSea());
  if (btnPause) {
    btnPause.addEventListener('click', () => {
      if (window.pauseSimulation) window.pauseSimulation();
      window.AppState.isLivingSeaRunning = false;
      if (window.PlaybackController) window.PlaybackController.updateLivingSeaButtonState();
    });
  }
  if (btnStep) {
    btnStep.addEventListener('click', () => {
      if (window.stepSimulation) window.stepSimulation(1);
      window.AppState.isLivingSeaRunning = true;
      if (window.PlaybackController) window.PlaybackController.updateLivingSeaButtonState();
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
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents);
    });
  }

  if (imuRateSelect) {
    imuRateSelect.addEventListener('change', (e) => {
      window.AppState.imuRate = parseInt(e.target.value, 10) || 100;
      loadScenario(
        window.AppState.scenarioId,
        window.AppState.seed,
        window.AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null
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
        window.TimelineRenderer ? window.TimelineRenderer.events : null
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
        window.TimelineRenderer ? window.TimelineRenderer.events : null
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
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, null);
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
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, []);
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

async function loadScenario(scenarioId, seed, durationS = 20, customEvents = null) {
  if (window.pauseSimulation) window.pauseSimulation();
  window.userConfirmedSail = null;

  try {
    const payload = {
      scenario: scenarioId,
      vessel_preset: window.AppState.vesselPreset || 'beneteau_oceanis_45',
      sail_plan: window.AppState.sailPlan || 'FULL_MAIN',
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
    window.AppState.currentSimTimeMs = 0.0;
    window.userConfirmedSail = null;
    window.queryActiveUntilMs = 0;
    window.queryTriggeredAtMs = 0;
    if (window.InstrumentRenderer) {
      window.InstrumentRenderer.reset();
    }
    
    if (window.TimelineRenderer) {
      window.TimelineRenderer.init(window.AppState.data, customEvents);
      window.TimelineRenderer.onEventsChanged = (updatedEvents) => {
        loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, updatedEvents);
      };
    }

    if (!window.AppState.isLivingSeaRunning) {
      if (window.renderZeroState) window.renderZeroState();
    } else {
      if (window.renderAtTime) window.renderAtTime(window.AppState.currentSimTimeMs);
    }
  } catch (err) {
    console.error('Failed to load scenario:', err);
  }
}

window.loadScenario = loadScenario;
