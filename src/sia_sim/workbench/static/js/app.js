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

function bindVesselControls() {
  const vesselSelect = document.getElementById('vesselSelect');
  const sailChips = document.querySelectorAll('.btn-sail-chip');
  const vesselPlanTag = document.getElementById('vesselPlanTag');
  const vspecLoa = document.getElementById('vspecLoa');
  const vspecBeam = document.getElementById('vspecBeam');
  const vspecMass = document.getElementById('vspecMass');
  const vspecArea = document.getElementById('vspecArea');

  const updateVesselSpecsDisplay = (vid) => {
    if (vid === 'beneteau_oceanis_45') {
      if (vspecLoa) vspecLoa.textContent = '13.94 m';
      if (vspecBeam) vspecBeam.textContent = '4.50 m';
      if (vspecMass) vspecMass.textContent = '10,550 kg';
      if (vspecArea) vspecArea.textContent = window.AppState.sailPlan === 'CODE_ZERO' ? '130 m²' : '100 m²';
    } else {
      if (vspecLoa) vspecLoa.textContent = '10.50 m';
      if (vspecBeam) vspecBeam.textContent = '3.20 m';
      if (vspecMass) vspecMass.textContent = '4,500 kg';
      if (vspecArea) vspecArea.textContent = '45 m²';
    }
  };

  if (vesselSelect) {
    vesselSelect.addEventListener('change', (e) => {
      window.AppState.vesselPreset = e.target.value;
      updateVesselSpecsDisplay(window.AppState.vesselPreset);
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
      loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents);
    });
  }

  if (sailChips) {
    sailChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const plan = chip.getAttribute('data-sail');
        window.AppState.sailPlan = plan;
        sailChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');

        if (vesselPlanTag) {
          vesselPlanTag.textContent = chip.textContent.trim();
        }
        updateVesselSpecsDisplay(window.AppState.vesselPreset);

        const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
        loadScenario(window.AppState.scenarioId, window.AppState.seed, window.AppState.durationS, existingEvents);
      });
    });
  }
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
