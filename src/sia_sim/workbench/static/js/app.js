/**
 * SIA Simulation Workbench — Core Application Controller
 */

const AppState = {
  scenarioId: 'sim005',
  seed: 42,
  data: null,
  currentTick: 0,
  isPlaying: false,
  playInterval: null,
  mode: 'live', // 'live' | 'debug'
};

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  bindControls();
  await loadScenario(AppState.scenarioId, AppState.seed);
}

function bindControls() {
  const btnRun = document.getElementById('btnRun');
  const btnPause = document.getElementById('btnPause');
  const btnStep = document.getElementById('btnStep');
  const btnReset = document.getElementById('btnReset');
  const scenarioSelect = document.getElementById('scenarioSelect');
  const seedInput = document.getElementById('seedInput');
  const btnModeLive = document.getElementById('btnModeLive');
  const btnModeDebug = document.getElementById('btnModeDebug');

  btnRun.addEventListener('click', () => playSimulation());
  btnPause.addEventListener('click', () => pauseSimulation());
  btnStep.addEventListener('click', () => stepSimulation(1));
  btnReset.addEventListener('click', () => resetSimulation());

  scenarioSelect.addEventListener('change', (e) => {
    AppState.scenarioId = e.target.value;
    loadScenario(AppState.scenarioId, AppState.seed);
  });

  seedInput.addEventListener('change', (e) => {
    AppState.seed = parseInt(e.target.value, 10) || 42;
    loadScenario(AppState.scenarioId, AppState.seed);
  });

  btnModeLive.addEventListener('click', () => setMode('live'));
  btnModeDebug.addEventListener('click', () => setMode('debug'));

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

function setMode(mode) {
  AppState.mode = mode;
  document.body.className = `mode-${mode}`;
  document.getElementById('btnModeLive').classList.toggle('active', mode === 'live');
  document.getElementById('btnModeDebug').classList.toggle('active', mode === 'debug');
}

async function loadScenario(scenarioId, seed) {
  pauseSimulation();
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioId, seed: seed }),
    });
    const json = await res.json();
    if (json.error) {
      alert(`Simulation run failed: ${json.error}`);
      return;
    }
    AppState.data = json;
    AppState.currentTick = 0;
    
    if (window.TimelineRenderer) {
      window.TimelineRenderer.init(AppState.data);
    }

    renderTick(0);
  } catch (err) {
    console.error('Failed to load scenario:', err);
  }
}

function playSimulation() {
  if (!AppState.data || AppState.isPlaying) return;
  AppState.isPlaying = true;
  document.getElementById('btnRun').disabled = true;
  document.getElementById('btnPause').disabled = false;

  // Playback at 2x real-time speed (5ms per 10ms tick) for responsive visualization
  AppState.playInterval = setInterval(() => {
    if (AppState.currentTick < AppState.data.ticks.length - 1) {
      AppState.currentTick++;
      renderTick(AppState.currentTick);
    } else {
      pauseSimulation();
    }
  }, 10);
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
  AppState.currentTick = 0;
  renderTick(0);
}

function renderTick(index) {
  if (!AppState.data || !AppState.data.ticks[index]) return;
  const tick = AppState.data.ticks[index];
  const totalTicks = AppState.data.total_ticks;

  // 1. Clock Display
  const totalSeconds = tick.sim_time_ms / 1000;
  const mins = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const secs = (totalSeconds % 60).toFixed(2).padStart(5, '0');
  document.getElementById('simTimeValue').textContent = `${mins}:${secs}`;
  document.getElementById('simTickValue').textContent = `[Tick ${index}/${totalTicks}]`;

  // 2. Timeline Cursor
  if (window.TimelineRenderer) {
    window.TimelineRenderer.updateCursor(index, totalTicks);
  }

  // 3. Zone 2: Ground Truth Lab Terminal
  const gt = tick.ground_truth;
  document.getElementById('gtTws').innerHTML = `${gt.tws_kt.toFixed(2)} <span class="term-unit">kt</span>`;
  document.getElementById('gtTwd').innerHTML = `${gt.twd_deg.toFixed(1)} <span class="term-unit">°</span>`;
  document.getElementById('gtWave').innerHTML = `${gt.wave_elevation_m.toFixed(2)} <span class="term-unit">m</span>`;
  document.getElementById('gtHeel').innerHTML = `${gt.heel_deg.toFixed(2)} <span class="term-unit">°</span>`;
  document.getElementById('gtPitch').innerHTML = `${gt.pitch_deg.toFixed(2)} <span class="term-unit">°</span>`;
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

  // 4. Zone 3: Sensor View (Marine Console Canvas Dials)
  const sf = tick.sensor_frame;
  const dialWindCanvas = document.getElementById('dialWindCanvas');
  const dialHeelCanvas = document.getElementById('dialHeelCanvas');
  const dialNavCanvas = document.getElementById('dialNavCanvas');

  InstrumentRenderer.drawWindDial(
    dialWindCanvas,
    sf.wind.apparent_wind_angle_deg,
    sf.wind.apparent_wind_speed_kt,
    sf.wind.fault
  );
  document.getElementById('valAws').innerHTML = sf.wind.apparent_wind_speed_kt !== null
    ? `${sf.wind.apparent_wind_speed_kt.toFixed(1)} <span class="unit">kt</span>`
    : `--- <span class="unit">NO SIGNAL</span>`;

  InstrumentRenderer.drawHeelDial(
    dialHeelCanvas,
    sf.imu.roll_deg,
    sf.imu.fault
  );
  document.getElementById('valHeel').innerHTML = sf.imu.roll_deg !== null
    ? `${sf.imu.roll_deg.toFixed(1)} <span class="unit">°</span>`
    : `--- <span class="unit">NO FIX</span>`;

  InstrumentRenderer.drawNavDial(
    dialNavCanvas,
    sf.gps.cog_deg,
    sf.gps.sog_kt,
    sf.gps.fault || sf.gps.fix_loss
  );
  document.getElementById('valSog').innerHTML = sf.gps.sog_kt !== null
    ? `${sf.gps.sog_kt.toFixed(1)} <span class="unit">kt</span>`
    : `--- <span class="unit">NO FIX</span>`;

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
  if (sel) {
    document.getElementById('primaryScore').textContent = `SCORE: ${sel.priority_score.toFixed(2)}`;
    document.getElementById('primaryActionTitle').textContent = sel.action_type.replace(/_/g, ' ');
    document.getElementById('cmdRudder').textContent = sel.rudder_command_deg !== null ? `${sel.rudder_command_deg.toFixed(1)}°` : 'NONE';
    document.getElementById('cmdSail').textContent = sel.sail_command_pct !== null ? `${sel.sail_command_pct.toFixed(0)}%` : 'MAINTAIN';
  } else {
    document.getElementById('primaryScore').textContent = 'SCORE: --';
    document.getElementById('primaryActionTitle').textContent = 'NO IMMEDIATE ACTION REQUIRED';
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
    candList.innerHTML = '<div class="candidate-row empty">None active</div>';
  }

  document.getElementById('siaReasoningNote').textContent = sia.note || 'Nominal monitoring';

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
}

window.AppState = AppState;
window.renderTick = renderTick;
