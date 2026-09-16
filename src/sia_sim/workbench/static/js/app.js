/**
 * SIA Simulation Workbench — Core Application Controller
 */

const AppState = {
  scenarioId: 'cruise',
  vesselPreset: 'beneteau_oceanis_45',
  sailPlan: 'FULL_MAIN',
  seed: 42,
  durationS: 20,
  imuRate: 100,
  damping: 'normal',
  customWorld: null,
  data: null,
  currentTick: 0,
  isPlaying: false,
  isLivingSeaRunning: false,
  speedMultiplier: 2.0,
  playInterval: null,
  mode: 'live', // 'live' | 'debug'
  selectedEvent: null,
};

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  bindControls();
  bindVesselControls();
  bindModalControls();
  bindCustomWorldControls();
  bindLivingSeaToggle();
  await loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS);
  renderZeroState(); // Initial state: boat is stationary at zero
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
      if (vspecArea) vspecArea.textContent = AppState.sailPlan === 'CODE_ZERO' ? '130 m²' : '100 m²';
    } else {
      if (vspecLoa) vspecLoa.textContent = '10.50 m';
      if (vspecBeam) vspecBeam.textContent = '3.20 m';
      if (vspecMass) vspecMass.textContent = '4,500 kg';
      if (vspecArea) vspecArea.textContent = '45 m²';
    }
  };

  if (vesselSelect) {
    vesselSelect.addEventListener('change', (e) => {
      AppState.vesselPreset = e.target.value;
      updateVesselSpecsDisplay(AppState.vesselPreset);
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
      loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS, existingEvents);
    });
  }

  if (sailChips) {
    sailChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const plan = chip.getAttribute('data-sail');
        AppState.sailPlan = plan;
        sailChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');

        if (vesselPlanTag) {
          vesselPlanTag.textContent = chip.textContent.trim();
        }
        updateVesselSpecsDisplay(AppState.vesselPreset);

        const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : null;
        loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS, existingEvents);
      });
    });
  }
}

function bindLivingSeaToggle() {
  const btn = document.getElementById('btnLivingSeaToggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (!AppState.isLivingSeaRunning) {
      startLivingSea();
    } else {
      stopLivingSeaToZero();
    }
  });
}

function startLivingSea() {
  AppState.isLivingSeaRunning = true;
  updateLivingSeaButtonState();
  if (AppState.currentTick === 0) {
    renderTick(0);
  }
  playSimulation();
}

function stopLivingSeaToZero() {
  AppState.isLivingSeaRunning = false;
  pauseSimulation();
  resetSimulation();
  renderZeroState();
  updateLivingSeaButtonState();
}

function updateLivingSeaButtonState() {
  const btn = document.getElementById('btnLivingSeaToggle');
  const icon = document.getElementById('seaToggleIcon');
  const label = document.getElementById('seaToggleLabel');
  if (!btn) return;

  if (AppState.isLivingSeaRunning) {
    btn.className = 'btn-living-sea-toggle state-running';
    if (icon) icon.textContent = '⏹';
    if (label) label.textContent = 'STOP SIMULATION (RESET TO ZERO)';
  } else {
    btn.className = 'btn-living-sea-toggle state-stopped';
    if (icon) icon.textContent = '▶';
    if (label) label.textContent = 'START SIMULATION';
  }
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

  btnRun.addEventListener('click', () => startLivingSea());
  btnPause.addEventListener('click', () => {
    pauseSimulation();
    AppState.isLivingSeaRunning = false;
    updateLivingSeaButtonState();
  });
  btnStep.addEventListener('click', () => {
    stepSimulation(1);
    AppState.isLivingSeaRunning = true;
    updateLivingSeaButtonState();
  });
  btnReset.addEventListener('click', () => stopLivingSeaToZero());

  if (scenarioSelect) {
    scenarioSelect.addEventListener('change', (e) => {
      AppState.scenarioId = e.target.value;
      AppState.customWorld = null; // reset custom override on preset change
      const durVal = durationSelect ? (parseInt(durationSelect.value, 10) || 20) : 20;
      AppState.durationS = durVal;
      // Preserve any events placed by human, or keep timeline clean if empty
      const existingEvents = window.TimelineRenderer ? window.TimelineRenderer.events : [];
      loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS, existingEvents);
    });
  }

  if (imuRateSelect) {
    imuRateSelect.addEventListener('change', (e) => {
      AppState.imuRate = parseInt(e.target.value, 10) || 100;
      loadScenario(
        AppState.scenarioId,
        AppState.seed,
        AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null
      );
    });
  }

  if (dampingSelect) {
    dampingSelect.addEventListener('change', (e) => {
      AppState.damping = e.target.value;
      if (window.InstrumentRenderer) {
        window.InstrumentRenderer.setDampingMode(AppState.damping);
      }
    });
  }

  if (durationSelect) {
    durationSelect.addEventListener('change', (e) => {
      AppState.durationS = parseInt(e.target.value, 10) || 20;
      loadScenario(
        AppState.scenarioId,
        AppState.seed,
        AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null
      );
    });
  }

  if (seedInput) {
    seedInput.addEventListener('change', (e) => {
      AppState.seed = parseInt(e.target.value, 10) || 42;
      loadScenario(
        AppState.scenarioId,
        AppState.seed,
        AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null
      );
    });
  }

  const speedSelect = document.getElementById('speedSelect');
  if (speedSelect) {
    speedSelect.addEventListener('change', (e) => {
      AppState.speedMultiplier = parseFloat(e.target.value) || 2.0;
      if (AppState.isPlaying) {
        pauseSimulation();
        playSimulation();
      }
    });
  }

  btnModeLive.addEventListener('click', () => setMode('live'));
  btnModeDebug.addEventListener('click', () => setMode('debug'));

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
      if (window.TimelineRenderer) {
        window.TimelineRenderer.events = [];
        window.TimelineRenderer.renderTracks();
      }
      loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS, []);
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
      loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS, []);
    });
  }

  // Keyboard shortcuts (Space = Play/Pause, ArrowRight = Step)
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.code === 'Space') {
      e.preventDefault();
      AppState.isPlaying ? pauseSimulation() : playSimulation();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      stepSimulation(1);
    }
  });
}

function bindCustomWorldControls() {
  const btnCustom = document.getElementById('btnCustomWorld');
  const backdrop = document.getElementById('customWorldModalBackdrop');
  const btnClose = document.getElementById('btnCustomWorldClose');
  const btnCancel = document.getElementById('btnCustomWorldCancel');
  const btnApply = document.getElementById('btnCustomWorldApply');

  if (btnCustom && backdrop) {
    btnCustom.addEventListener('click', () => {
      backdrop.style.display = 'flex';
    });
  }

  const closeCustomModal = () => {
    if (backdrop) backdrop.style.display = 'none';
  };

  if (btnClose) btnClose.addEventListener('click', closeCustomModal);
  if (btnCancel) btnCancel.addEventListener('click', closeCustomModal);

  if (btnApply) {
    btnApply.addEventListener('click', () => {
      const tws = parseFloat(document.getElementById('customTws').value) || 13.0;
      const twa = parseFloat(document.getElementById('customTwa').value) || 0.0;
      const waveH = parseFloat(document.getElementById('customWaveHeight').value) || 1.0;
      const waveT = parseFloat(document.getElementById('customWavePeriod').value) || 4.5;
      const sog = parseFloat(document.getElementById('customSog').value) || 5.8;
      const heading = parseFloat(document.getElementById('customHeading').value) || 65.0;
      const heel = parseFloat(document.getElementById('customHeel').value) || -12.0;

      AppState.customWorld = {
        initial_tws_kt: tws,
        initial_twa_deg: twa,
        initial_wave_height_m: waveH,
        initial_wave_period_s: waveT,
        initial_sog_kt: sog,
        initial_heading_deg: heading,
        initial_heel_deg: heel,
      };

      closeCustomModal();
      loadScenario(
        AppState.scenarioId,
        AppState.seed,
        AppState.durationS,
        window.TimelineRenderer ? window.TimelineRenderer.events : null
      );
    });
  }
}

function bindModalControls() {
  const backdrop = document.getElementById('eventModalBackdrop');
  const btnClose = document.getElementById('btnEventModalClose');
  const btnSave = document.getElementById('btnEventSave');
  const btnDelete = document.getElementById('btnEventDelete');
  const selectType = document.getElementById('modalEventType');

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      if (backdrop) backdrop.style.display = 'none';
      AppState.selectedEvent = null;
    });
  }

  if (selectType) {
    selectType.addEventListener('change', (e) => {
      const unit = document.getElementById('modalParamUnit');
      if (unit) {
        unit.textContent = e.target.value === 'wind_gust' ? 'kt' : (e.target.value === 'wave_impact' ? 'kN' : '');
      }
    });
  }

  if (btnDelete) {
    btnDelete.addEventListener('click', () => {
      if (AppState.selectedEvent && window.TimelineRenderer) {
        window.TimelineRenderer.deleteEvent(AppState.selectedEvent.event_id);
      }
      if (backdrop) backdrop.style.display = 'none';
      AppState.selectedEvent = null;
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', () => {
      if (!AppState.selectedEvent) return;
      const timeSec = parseFloat(document.getElementById('modalEventTime').value) || 0.0;
      const durSec = parseFloat(document.getElementById('modalEventDuration').value) || 2.0;
      const timeMs = Math.round(timeSec * 1000);
      const durMs = Math.round(durSec * 1000);
      const type = document.getElementById('modalEventType').value;
      const paramVal = parseFloat(document.getElementById('modalEventParam').value) || 10.0;

      AppState.selectedEvent.sim_time_ms = timeMs;
      AppState.selectedEvent.event_type = type;

      if (type === 'wind_gust') {
        AppState.selectedEvent.parameters = {
          tws_kt: paramVal,
          duration_ms: durMs,
          duration_s: durSec,
          direction_shift_deg: 15.0,
        };
      } else if (type === 'wave_impact') {
        AppState.selectedEvent.parameters = {
          impact_force_n: paramVal * 1000.0,
          impact_roll_moment_nm: -paramVal * 2000.0,
          duration_ms: durMs,
          duration_s: durSec,
        };
      } else {
        AppState.selectedEvent.parameters = {
          sensor: 'imu',
          duration_ms: durMs,
          duration_s: durSec,
        };
      }

      if (window.TimelineRenderer) {
        window.TimelineRenderer.renderTracks();
        if (window.TimelineRenderer.onEventsChanged) {
          window.TimelineRenderer.onEventsChanged(window.TimelineRenderer.events);
        }
      }

      if (backdrop) backdrop.style.display = 'none';
      AppState.selectedEvent = null;
    });
  }
}

function openEventInspector(evt) {
  AppState.selectedEvent = evt;
  const backdrop = document.getElementById('eventModalBackdrop');
  if (!backdrop) return;

  document.getElementById('modalEventId').value = evt.event_id;
  document.getElementById('modalEventType').value = evt.event_type;
  document.getElementById('modalEventTime').value = (evt.sim_time_ms / 1000).toFixed(1);

  const durMs = evt.parameters.duration_ms || (evt.parameters.duration_s ? evt.parameters.duration_s * 1000 : 2000);
  document.getElementById('modalEventDuration').value = (durMs / 1000).toFixed(1);

  let paramVal = 10;
  if (evt.event_type === 'wind_gust') {
    paramVal = evt.parameters.tws_kt || 18;
    document.getElementById('modalParamUnit').textContent = 'kt';
  } else if (evt.event_type === 'wave_impact') {
    paramVal = (evt.parameters.impact_force_n || 12000) / 1000;
    document.getElementById('modalParamUnit').textContent = 'kN';
  } else {
    paramVal = 1;
    document.getElementById('modalParamUnit').textContent = '';
  }
  document.getElementById('modalEventParam').value = paramVal;

  backdrop.style.display = 'flex';
}

window.openEventInspector = openEventInspector;

function setMode(mode) {
  AppState.mode = mode;
  document.body.className = `mode-${mode}`;
  document.getElementById('btnModeLive').classList.toggle('active', mode === 'live');
  document.getElementById('btnModeDebug').classList.toggle('active', mode === 'debug');
}

async function loadScenario(scenarioId, seed, durationS = 20, customEvents = null) {
  pauseSimulation();
  window.userConfirmedSail = null;

  const btnToggle = document.getElementById('btnLivingSeaToggle');
  const durStr = durationS >= 3600 ? `${(durationS / 3600).toFixed(0)}h` : `${durationS}s`;

  try {
    const payload = {
      scenario: scenarioId,
      vessel_preset: AppState.vesselPreset || 'beneteau_oceanis_45',
      sail_plan: AppState.sailPlan || 'FULL_MAIN',
      seed: seed,
      duration_ms: durationS * 1000,
      imu_sample_rate_hz: AppState.imuRate,
    };
    if (customEvents !== null) {
      payload.events = customEvents;
    }
    if (AppState.customWorld) {
      payload.custom_world = AppState.customWorld;
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
    AppState.data = json;
    AppState.currentTick = 0;
    if (window.InstrumentRenderer) {
      window.InstrumentRenderer.reset();
    }
    
    if (window.TimelineRenderer) {
      window.TimelineRenderer.init(AppState.data, customEvents);
      window.TimelineRenderer.onEventsChanged = (updatedEvents) => {
        loadScenario(AppState.scenarioId, AppState.seed, AppState.durationS, updatedEvents);
      };
    }

    if (!AppState.isLivingSeaRunning) {
      renderZeroState();
    } else {
      renderTick(AppState.currentTick);
    }
  } catch (err) {
    console.error('Failed to load scenario:', err);
  }
}

function playSimulation() {
  if (!AppState.data || AppState.isPlaying) return;
  AppState.isPlaying = true;
  document.getElementById('btnRun').disabled = true;
  document.getElementById('btnPause').disabled = false;

  const totalFrames = AppState.data.ticks.length;
  const simDurationMs = AppState.data.duration_ms || 20000;
  const simDtPerFrameMs = simDurationMs / Math.max(1, totalFrames);

  // Smooth 60 FPS playback timer (16ms per frame)
  const timerIntervalMs = 16;
  AppState.playInterval = setInterval(() => {
    if (AppState.currentTick < totalFrames - 1) {
      const simMsToAdvance = timerIntervalMs * AppState.speedMultiplier;
      const framesToAdvance = Math.max(1, Math.round(simMsToAdvance / simDtPerFrameMs));
      AppState.currentTick = Math.min(totalFrames - 1, AppState.currentTick + framesToAdvance);
      renderTick(AppState.currentTick);
    } else {
      pauseSimulation();
    }
  }, timerIntervalMs);
}

function pauseSimulation() {
  AppState.isPlaying = false;
  clearInterval(AppState.playInterval);
  document.getElementById('btnRun').disabled = false;
  document.getElementById('btnPause').disabled = true;
}

function stepSimulation(stepCount = 1) {
  if (!AppState.data) return;
  pauseSimulation();
  AppState.currentTick = Math.min(AppState.data.ticks.length - 1, AppState.currentTick + stepCount);
  renderTick(AppState.currentTick);
}

function resetSimulation() {
  pauseSimulation();
  if (window.InstrumentRenderer) {
    window.InstrumentRenderer.reset();
  }
  AppState.currentTick = 0;
  renderZeroState();
}

function renderZeroState() {
  if (window.InstrumentRenderer) {
    window.InstrumentRenderer.reset();
  }

  // 1. Clock Display at zero
  const durationMs = AppState.data ? AppState.data.duration_ms : AppState.durationS * 1000;
  const totalPhysicalTicks = AppState.data ? (AppState.data.total_ticks || Math.round(durationMs / 10)) : Math.round(durationMs / 10);
  const totalFrames = AppState.data ? AppState.data.ticks.length : 2000;

  let timeStr = '00:00.00';
  if (durationMs >= 3600000) {
    timeStr = '00:00:00';
  }
  document.getElementById('simTimeValue').textContent = timeStr;

  if (window.TimelineRenderer && AppState.data) {
    window.TimelineRenderer.updateCursor(0, totalFrames);
  }

  // 2. Ground truth zeros
  document.getElementById('gtTws').innerHTML = `0.00 <span class="term-unit">kt</span>`;
  document.getElementById('gtTwd').innerHTML = `000.0 <span class="term-unit">°</span>`;
  document.getElementById('gtWave').innerHTML = `0.00 <span class="term-unit">m</span>`;
  document.getElementById('gtHeave').innerHTML = `0.00 <span class="term-unit">m</span>`;
  document.getElementById('gtSlamForce').innerHTML = `0.0 <span class="term-unit">kN</span>`;
  document.getElementById('gtHeel').innerHTML = `0.00 <span class="term-unit">°</span>`;
  document.getElementById('gtPitch').innerHTML = `0.00 <span class="term-unit">°</span>`;
  document.getElementById('gtYaw').innerHTML = `000.0 <span class="term-unit">°</span>`;
  document.getElementById('gtSog').innerHTML = `0.00 <span class="term-unit">kt</span>`;
  document.getElementById('gtRudder').innerHTML = `0.0 <span class="term-unit">°</span>`;
  document.getElementById('gtHydroLoss').textContent = `0 %`;
  document.getElementById('gtActiveEvents').textContent = 'NONE';
  const gtStateTag = document.getElementById('gtStateTag');
  if (gtStateTag) {
    gtStateTag.textContent = 'STATUS: DOCKED / IDLE';
    gtStateTag.style.color = '#94a3b8';
  }

  // 3. Marine Dials Zeros
  const dialWindCanvas = document.getElementById('dialWindCanvas');
  const dialHeelCanvas = document.getElementById('dialHeelCanvas');
  const dialPitchCanvas = document.getElementById('dialPitchCanvas');
  const dialNavCanvas = document.getElementById('dialNavCanvas');
  const dialHeaveCanvas = document.getElementById('dialHeaveCanvas');
  const dialSlamCanvas = document.getElementById('dialSlamCanvas');

  if (dialWindCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawWindDial(dialWindCanvas, 0.0, 0.0, false);
  }
  if (dialHeelCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawHeelDial(dialHeelCanvas, 0.0, false);
  }
  if (dialPitchCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawPitchDial(dialPitchCanvas, 0.0, 0.0, false);
  }
  if (dialNavCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawNavDial(dialNavCanvas, 0.0, 0.0, false);
  }
  if (dialHeaveCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawHeaveGauge(dialHeaveCanvas, 0.0, 9.80665, false);
  }
  if (dialSlamCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawSlammingGauge(dialSlamCanvas, 0.0, false, 15.0, false);
  }

  const valAws = document.getElementById('valAws');
  if (valAws) valAws.innerHTML = `0.0 <span class="unit">kt</span>`;

  const valHeel = document.getElementById('valHeel');
  if (valHeel) valHeel.innerHTML = `0.0 <span class="unit">°</span>`;

  const valPitch = document.getElementById('valPitch');
  if (valPitch) valPitch.innerHTML = `0.0 <span class="unit">°</span>`;

  const valSog = document.getElementById('valSog');
  if (valSog) valSog.innerHTML = `0.0 <span class="unit">kt</span>`;

  const valHeave = document.getElementById('valHeave');
  if (valHeave) valHeave.innerHTML = `1.00 <span class="unit">g</span>`;

  const valHeaveAccel = document.getElementById('valHeaveAccel');
  if (valHeaveAccel) valHeaveAccel.innerHTML = `1.00 <span class="unit">g</span>`;

  const valSlamForce = document.getElementById('valSlamForce');
  if (valSlamForce) valSlamForce.innerHTML = `0.0 <span class="unit">kN</span>`;

  const valPitchRate = document.getElementById('valPitchRate');
  if (valPitchRate) valPitchRate.textContent = '0.0 °/s';

  const valYawRate = document.getElementById('valYawRate');
  if (valYawRate) valYawRate.textContent = '0.0 °/s';

  const valRudderSensor = document.getElementById('valRudderSensor');
  if (valRudderSensor) valRudderSensor.textContent = '0.0 °';

  const valSailSensor = document.getElementById('valSailSensor');
  if (valSailSensor) valSailSensor.textContent = '100 %';

  const chipImu = document.getElementById('chipImu');
  if (chipImu) {
    chipImu.className = 'health-chip chip-ok';
    chipImu.textContent = 'IMU: IDLE';
  }
  const chipGps = document.getElementById('chipGps');
  if (chipGps) {
    chipGps.className = 'health-chip chip-ok';
    chipGps.textContent = 'GPS: IDLE';
  }
  const chipWind = document.getElementById('chipWind');
  if (chipWind) {
    chipWind.className = 'health-chip chip-ok';
    chipWind.textContent = 'WIND: IDLE';
  }

  // 4. SIA Advisory Panel at IDLE
  const siaHazardBadge = document.getElementById('siaHazardBadge');
  if (siaHazardBadge) {
    siaHazardBadge.className = 'hazard-badge nominal';
    siaHazardBadge.style.background = '';
    siaHazardBadge.style.color = '';
    siaHazardBadge.textContent = 'IDLE';
  }
  document.getElementById('siaRiskVal').textContent = '0.00';
  document.getElementById('siaRiskBar').style.width = '0%';
  document.getElementById('siaConfVal').textContent = '1.00';
  document.getElementById('siaConfBar').style.width = '100%';

  const primaryCardTag = document.getElementById('primaryCardTag');
  if (primaryCardTag) primaryCardTag.textContent = 'SYSTEM IDLE (PRESS START TO SAIL)';
  document.getElementById('primaryScore').textContent = 'STATUS: IDLE';
  document.getElementById('primaryActionTitle').textContent = 'BOAT AT MOORINGS / STANDBY';
  document.getElementById('cmdRudder').textContent = '0.0°';
  document.getElementById('cmdSail').textContent = '0%';
  document.getElementById('siaReasoningNote').textContent = 'Simulation stopped. Boat is stationary at moorings with all dials at zero.';

  const candList = document.getElementById('candidatesList');
  if (candList) candList.innerHTML = '<div class="candidate-row empty">Simulation stopped (Waiting for START)</div>';

  // 5. Query loop at standby
  const queryCard = document.getElementById('zoneQueryLoop');
  const queryPrompt = document.getElementById('queryPromptText');
  if (queryCard) {
    queryCard.className = 'zone-card zone-query-loop standby';
  }
  if (queryPrompt) {
    queryPrompt.textContent = 'SIA Core: "Living sea standby. Start simulation to monitor dynamics."';
  }

  // 6. Evaluator at Standby
  const footerVerdict = document.getElementById('footerVerdict');
  if (footerVerdict) {
    footerVerdict.className = 'verdict-badge';
    footerVerdict.style.background = 'rgba(148, 163, 184, 0.15)';
    footerVerdict.style.color = '#94a3b8';
    footerVerdict.textContent = 'VERDICT: STANDBY';
  }
}

function renderTick(index) {
  if (!AppState.data || !AppState.data.ticks[index]) return;
  const tick = AppState.data.ticks[index];
  const totalPhysicalTicks = AppState.data.total_ticks || Math.round(AppState.data.duration_ms / 10);
  const currentPhysicalTick = Math.round(tick.sim_time_ms / 10);
  const totalFrames = AppState.data.ticks.length;

  // 1. Clock Display (Adaptive for seconds, minutes, and hours)
  const totalSeconds = tick.sim_time_ms / 1000;
  let timeStr = '';
  if (AppState.data && AppState.data.duration_ms >= 3600000) {
    const hh = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
    const mm = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
    const ss = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
    timeStr = `${hh}:${mm}:${ss}`;
  } else {
    const mins = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const secs = (totalSeconds % 60).toFixed(2).padStart(5, '0');
    timeStr = `${mins}:${secs}`;
  }
  document.getElementById('simTimeValue').textContent = timeStr;

  // 2. Timeline Cursor
  if (window.TimelineRenderer) {
    window.TimelineRenderer.updateCursor(index, totalFrames);
  }

  // 3. Zone 2: Ground Truth Lab Terminal
  const gt = tick.ground_truth;
  document.getElementById('gtTws').innerHTML = `${gt.tws_kt.toFixed(2)} <span class="term-unit">kt</span>`;
  document.getElementById('gtTwd').innerHTML = `${gt.twd_deg.toFixed(1)} <span class="term-unit">°</span>`;
  document.getElementById('gtWave').innerHTML = `${gt.wave_elevation_m.toFixed(2)} <span class="term-unit">m</span>`;
  document.getElementById('gtHeave').innerHTML = `${(gt.heave_m || 0.0).toFixed(2)} <span class="term-unit">m</span>`;
  document.getElementById('gtSlamForce').innerHTML = `${(gt.slam_force_kn || 0.0).toFixed(1)} <span class="term-unit">kN</span>`;
  document.getElementById('gtHeel').innerHTML = `${gt.heel_deg.toFixed(2)} <span class="term-unit">°</span>`;
  document.getElementById('gtPitch').innerHTML = `${(gt.pitch_deg || 0.0).toFixed(2)} <span class="term-unit">°</span>`;
  document.getElementById('gtYaw').innerHTML = `${gt.yaw_deg.toFixed(1)} <span class="term-unit">°</span>`;
  document.getElementById('gtSog').innerHTML = `${gt.sog_kt.toFixed(2)} <span class="term-unit">kt</span>`;
  document.getElementById('gtRudder').innerHTML = `${gt.rudder_deg.toFixed(1)} <span class="term-unit">°</span>`;
  document.getElementById('gtHydroLoss').textContent = `${Math.round(gt.rudder_hydro_loss * 100)} %`;
  
  const activeEvents = gt.active_events.length > 0 ? gt.active_events.join(', ') : 'NONE';
  document.getElementById('gtActiveEvents').textContent = activeEvents;

  // Hydro status tag
  const gtStateTag = document.getElementById('gtStateTag');
  if (gt.rudder_hydro_loss > 0.4) {
    gtStateTag.textContent = 'HYDRO: STALL / SEPARATION';
    gtStateTag.style.color = '#ff1744';
  } else if (gt.rudder_hydro_loss > 0.1) {
    gtStateTag.textContent = 'HYDRO: REDUCED LIFT';
    gtStateTag.style.color = '#ffb300';
  } else {
    gtStateTag.textContent = 'HYDRO: NOMINAL';
    gtStateTag.style.color = '#94a3b8';
  }

  // 4. Zone 3: Sensor View (6 Marine Console Canvas Dials)
  const sf = tick.sensor_frame;
  const dialWindCanvas = document.getElementById('dialWindCanvas');
  const dialHeelCanvas = document.getElementById('dialHeelCanvas');
  const dialPitchCanvas = document.getElementById('dialPitchCanvas');
  const dialNavCanvas = document.getElementById('dialNavCanvas');
  const dialHeaveCanvas = document.getElementById('dialHeaveCanvas');
  const dialSlamCanvas = document.getElementById('dialSlamCanvas');

  // 1. Wind Dial
  if (dialWindCanvas) {
    InstrumentRenderer.drawWindDial(
      dialWindCanvas,
      sf.wind.apparent_wind_angle_deg,
      sf.wind.apparent_wind_speed_kt,
      sf.wind.fault
    );
  }
  document.getElementById('valAws').innerHTML = sf.wind.apparent_wind_speed_kt !== null
    ? `${sf.wind.apparent_wind_speed_kt.toFixed(1)} <span class="unit">kt</span>`
    : `--- <span class="unit">NO SIGNAL</span>`;

  // 2. Heel Dial
  if (dialHeelCanvas) {
    InstrumentRenderer.drawHeelDial(
      dialHeelCanvas,
      sf.imu.roll_deg,
      sf.imu.fault
    );
  }
  document.getElementById('valHeel').innerHTML = sf.imu.roll_deg !== null
    ? `${sf.imu.roll_deg.toFixed(1)} <span class="unit">°</span>`
    : `--- <span class="unit">NO FIX</span>`;

  // 3. Pitch Dial (Килевая качка)
  if (dialPitchCanvas) {
    InstrumentRenderer.drawPitchDial(
      dialPitchCanvas,
      sf.imu.pitch_deg,
      sf.imu.pitch_rate_deg_s,
      sf.imu.fault
    );
  }
  const valPitchEl = document.getElementById('valPitch');
  if (valPitchEl) {
    valPitchEl.innerHTML = sf.imu.pitch_deg !== null
      ? `${sf.imu.pitch_deg.toFixed(1)} <span class="unit">°</span>`
      : `--- <span class="unit">NO FIX</span>`;
  }

  // 4. Nav / SOG Dial
  if (dialNavCanvas) {
    InstrumentRenderer.drawNavDial(
      dialNavCanvas,
      sf.gps.cog_deg,
      sf.gps.sog_kt,
      sf.gps.fault || sf.gps.fix_loss
    );
  }
  document.getElementById('valSog').innerHTML = sf.gps.sog_kt !== null
    ? `${sf.gps.sog_kt.toFixed(1)} <span class="unit">kt</span>`
    : `--- <span class="unit">NO FIX</span>`;

  // 5. Heave & Accel Az Dial (Вертикальная качка)
  if (dialHeaveCanvas) {
    InstrumentRenderer.drawHeaveGauge(
      dialHeaveCanvas,
      gt.heave_m || 0.0,
      sf.imu.accel_z_m_s2 !== null ? sf.imu.accel_z_m_s2 : 9.81,
      sf.imu.fault
    );
  }
  const valHeaveEl = document.getElementById('valHeaveAccel');
  if (valHeaveEl) {
    const gVal = sf.imu.accel_z_m_s2 !== null ? (sf.imu.accel_z_m_s2 / 9.80665).toFixed(2) : '1.00';
    valHeaveEl.innerHTML = sf.imu.accel_z_m_s2 !== null
      ? `${gVal} <span class="unit">g</span>`
      : `--- <span class="unit">NO FIX</span>`;
  }

  // 6. Slamming & Hull Shock Meter (Слеминг)
  const isSlamming = gt.slam_active || (gt.slam_force_kn && gt.slam_force_kn > 5.0);
  if (dialSlamCanvas) {
    InstrumentRenderer.drawSlammingGauge(
      dialSlamCanvas,
      gt.slam_force_kn || 0.0,
      isSlamming,
      15.0,
      sf.imu.fault
    );
  }
  const cardSlam = document.getElementById('cardSlamming');
  if (cardSlam) {
    cardSlam.classList.toggle('slam-active', isSlamming);
  }
  const valSlamEl = document.getElementById('valSlamForce');
  if (valSlamEl) {
    valSlamEl.innerHTML = `${(gt.slam_force_kn || 0.0).toFixed(1)} <span class="unit">kN</span>`;
  }

  // Sensor strip
  document.getElementById('valPitchRate').textContent = sf.imu.pitch_rate_deg_s !== null ? `${sf.imu.pitch_rate_deg_s.toFixed(1)} °/s` : '---';
  document.getElementById('valYawRate').textContent = sf.imu.yaw_rate_deg_s !== null ? `${sf.imu.yaw_rate_deg_s.toFixed(1)} °/s` : '---';
  document.getElementById('valRudderSensor').textContent = sf.actuators.rudder_angle_deg !== null ? `${sf.actuators.rudder_angle_deg.toFixed(1)} °` : '---';
  document.getElementById('valSailSensor').textContent = sf.actuators.mainsheet_pct !== null ? `${sf.actuators.mainsheet_pct.toFixed(0)} %` : 'UNKNOWN (ABSENT)';

  // Health chips
  const chipImu = document.getElementById('chipImu');
  chipImu.className = sf.imu.fault ? 'health-chip chip-fault' : 'health-chip chip-ok';
  chipImu.textContent = sf.imu.fault ? 'IMU: FAULT' : 'IMU: OK';

  const chipGps = document.getElementById('chipGps');
  chipGps.className = (sf.gps.fault || sf.gps.fix_loss) ? 'health-chip chip-fault' : 'health-chip chip-ok';
  chipGps.textContent = sf.gps.fault ? 'GPS: FAULT' : (sf.gps.fix_loss ? 'GPS: NO FIX' : 'GPS: OK');

  const chipWind = document.getElementById('chipWind');
  chipWind.className = sf.wind.fault ? 'health-chip chip-fault' : 'health-chip chip-ok';
  chipWind.textContent = sf.wind.fault ? 'WIND: FAULT' : 'WIND: OK';

  // 5. Zone 4: SIA Advisory & Reasoning
  const sia = tick.sia_decision;
  const siaHazardBadge = document.getElementById('siaHazardBadge');
  if (sia.hazard_id === 'HAZ-BROACH-PRECURSOR') {
    siaHazardBadge.className = 'hazard-badge critical';
    siaHazardBadge.textContent = '⚠ BROACH PRECURSOR';
  } else if (sia.hazard_id === 'HAZ-HEEL-ADVISORY') {
    siaHazardBadge.className = 'hazard-badge';
    siaHazardBadge.style.background = 'rgba(255, 179, 0, 0.2)';
    siaHazardBadge.style.color = '#ffb300';
    siaHazardBadge.textContent = 'HEEL ADVISORY';
  } else {
    siaHazardBadge.className = 'hazard-badge nominal';
    siaHazardBadge.style.background = '';
    siaHazardBadge.style.color = '';
    siaHazardBadge.textContent = 'NOMINAL';
  }

  document.getElementById('siaRiskVal').textContent = sia.risk_score.toFixed(2);
  document.getElementById('siaRiskBar').style.width = `${Math.min(100, sia.risk_score * 100)}%`;
  document.getElementById('siaConfVal').textContent = sia.confidence.toFixed(2);
  document.getElementById('siaConfBar').style.width = `${Math.min(100, sia.confidence * 100)}%`;

  // Primary Decision Card
  const sel = sia.selected_response;
  const primaryCardTag = document.getElementById('primaryCardTag');

  if (sel) {
    if (primaryCardTag) primaryCardTag.textContent = 'PRIMARY RECOMMENDED ACTION (HAZARD ACTIVE)';
    document.getElementById('primaryScore').textContent = `SCORE: ${sel.priority_score.toFixed(2)}`;
    document.getElementById('primaryActionTitle').textContent = sel.action_type.replace(/_/g, ' ');
    document.getElementById('cmdRudder').textContent = sel.rudder_command_deg !== null ? `${sel.rudder_command_deg.toFixed(1)}°` : 'NONE';
    document.getElementById('cmdSail').textContent = sel.sail_command_pct !== null ? `${sel.sail_command_pct.toFixed(0)}%` : 'MAINTAIN';
  } else {
    if (primaryCardTag) primaryCardTag.textContent = 'CONTINUOUS SAFETY MONITORING (NOMINAL)';
    document.getElementById('primaryScore').textContent = 'STATUS: SAFE';
    document.getElementById('primaryActionTitle').textContent = 'MAINTAIN COURSE & MONITOR TRIM';
    document.getElementById('cmdRudder').textContent = '0.0°';
    document.getElementById('cmdSail').textContent = '100%';
  }

  // Candidate Alternatives (fixed slots)
  const candList = document.getElementById('candidatesList');
  candList.innerHTML = '';
  if (sia.candidates && sia.candidates.length > 0) {
    sia.candidates.slice(0, 3).forEach((c, idx) => {
      const row = document.createElement('div');
      row.className = 'candidate-row';
      row.innerHTML = `
        <span class="cand-name">${idx + 1}. ${c.action_type.replace(/_/g, ' ')}</span>
        <span class="cand-score">Score: ${c.priority_score.toFixed(2)}</span>
      `;
      candList.appendChild(row);
    });
  } else {
    candList.innerHTML = '<div class="candidate-row empty">None active (Nominal cruising state)</div>';
  }

  document.getElementById('siaReasoningNote').textContent = sia.note || 'Nominal monitoring active';

  // 6. Footer Evaluator Status
  const evalData = AppState.data.evaluation;
  const footerEnvelope = document.getElementById('footerEnvelope');
  const oracle = tick.oracle;

  if (oracle.safe_envelope_intact) {
    footerEnvelope.className = 'footer-val val-pass';
    footerEnvelope.textContent = `INTACT (Margin: ${oracle.safety_margin_pct}%)`;
  } else {
    footerEnvelope.className = 'footer-val highlight-danger';
    footerEnvelope.textContent = 'BREACHED (>35° KNOCKDOWN)';
  }

  if (evalData.detection_latency_ms !== null) {
    document.getElementById('footerLatency').textContent = `${evalData.detection_latency_ms} ms (Target < 500 ms)`;
  } else {
    document.getElementById('footerLatency').textContent = 'N/A (No Hazard)';
  }

  document.getElementById('footerFalseAlarms').textContent = evalData.false_positives.toString();
  
  const footerVerdict = document.getElementById('footerVerdict');
  footerVerdict.className = evalData.verdict === 'PASS' ? 'verdict-badge badge-pass' : 'verdict-badge badge-fail';
  footerVerdict.textContent = `VERDICT: ${evalData.verdict} (M6)`;

  // 7. Dynamic Query Loop Display (Standby vs Active Hazard Context Refinement)
  if (window.updateQueryLoopDisplay) {
    window.updateQueryLoopDisplay(tick);
  }
}

window.AppState = AppState;
window.renderTick = renderTick;
