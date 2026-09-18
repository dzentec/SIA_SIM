/**
 * SIA Simulation Workbench — Playback & Rendering Controller Module
 */

function lerp(a, b, t) {
  if (a === null || a === undefined) return b;
  if (b === null || b === undefined) return a;
  return a + (b - a) * t;
}

function lerpAngle(a, b, t) {
  if (a === null || a === undefined) return b;
  if (b === null || b === undefined) return a;
  let diff = (b - a) % 360;
  if (diff > 180) diff -= 360;
  if (diff < -180) diff += 360;
  return a + diff * t;
}

function getInterpolatedStateAtTime(simTimeMs) {
  const state = window.AppState;
  if (!state.data || !state.data.ticks || state.data.ticks.length === 0) {
    return null;
  }
  const ticks = state.data.ticks;
  if (simTimeMs <= ticks[0].sim_time_ms) {
    return { tick: ticks[0], nextTick: ticks[0], alpha: 0, timeMs: simTimeMs };
  }
  if (simTimeMs >= ticks[ticks.length - 1].sim_time_ms) {
    const last = ticks[ticks.length - 1];
    return { tick: last, nextTick: last, alpha: 0, timeMs: simTimeMs };
  }

  // Binary search for left bounding keyframe
  let low = 0;
  let high = ticks.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (ticks[mid].sim_time_ms <= simTimeMs) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  const idxA = Math.max(0, high);
  const idxB = Math.min(ticks.length - 1, idxA + 1);
  const tA = ticks[idxA].sim_time_ms;
  const tB = ticks[idxB].sim_time_ms;
  const alpha = (tB > tA) ? Math.max(0, Math.min(1, (simTimeMs - tA) / (tB - tA))) : 0;
  return { tick: ticks[idxA], nextTick: ticks[idxB], alpha: alpha, timeMs: simTimeMs };
}

function playSimulation() {
  const state = window.AppState;
  if (!state.data || state.isPlaying) return;
  state.isPlaying = true;
  state.isLivingSeaRunning = true;
  const btnRun = document.getElementById('btnRun');
  const btnPause = document.getElementById('btnPause');
  if (btnRun) btnRun.disabled = true;
  if (btnPause) btnPause.disabled = false;
  updateLivingSeaButtonState();
  state.lastWallTimestamp = performance.now();

  if (window.Logger) {
    window.Logger.log('SIM_RUNNER', 'INFO', `Воспроизведение запущено с t=${(state.currentSimTimeMs / 1000).toFixed(2)}с (Скорость: ${state.speedMultiplier}x)`, null, state.currentSimTimeMs);
  }

  function loop(now) {
    if (!state.isPlaying) return;
    const elapsedWallMs = Math.min(200, now - state.lastWallTimestamp);
    state.lastWallTimestamp = now;

    const simMsDelta = elapsedWallMs * state.speedMultiplier;
    state.currentSimTimeMs += simMsDelta;

    const totalDurationMs = state.data.duration_ms || 20000;
    if (state.currentSimTimeMs >= totalDurationMs) {
      state.currentSimTimeMs = totalDurationMs;
      renderAtTime(state.currentSimTimeMs);
      pauseSimulation();
      if (window.Logger) {
        window.Logger.log('SIM_RUNNER', 'INFO', 'Достигнут конец симуляции (Complete).', null, totalDurationMs);
      }
      return;
    }

    renderAtTime(state.currentSimTimeMs);
    state.rafId = requestAnimationFrame(loop);
  }

  state.rafId = requestAnimationFrame(loop);
}

function pauseSimulation() {
  const state = window.AppState;
  if (state.isPlaying && window.Logger) {
    window.Logger.log('SIM_RUNNER', 'INFO', `Симуляция на паузе (t=${(state.currentSimTimeMs / 1000).toFixed(2)}с).`, null, state.currentSimTimeMs);
  }
  state.isPlaying = false;
  if (state.rafId) {
    cancelAnimationFrame(state.rafId);
    state.rafId = null;
  }
  state.lastWallTimestamp = null;
  const btnRun = document.getElementById('btnRun');
  const btnPause = document.getElementById('btnPause');
  if (btnRun) btnRun.disabled = false;
  if (btnPause) btnPause.disabled = true;
  updateLivingSeaButtonState();
}

function stepSimulation(stepSeconds = 0.5) {
  const state = window.AppState;
  if (!state.data) return;
  pauseSimulation();
  const totalDurationMs = state.data.duration_ms || 20000;
  state.currentSimTimeMs = Math.min(totalDurationMs, state.currentSimTimeMs + (stepSeconds * 1000));
  renderAtTime(state.currentSimTimeMs);
}

function resetSimulation() {
  pauseSimulation();
  if (window.InstrumentRenderer) {
    window.InstrumentRenderer.reset();
  }
  window.AppState.currentSimTimeMs = 0.0;
  window.AppState.isLivingSeaRunning = false;
  renderZeroState();
  updateLivingSeaButtonState();
  if (window.Logger) {
    window.Logger.log('SIM_RUNNER', 'INFO', 'Сброс приборов и времени симуляции на 0.00с.', null, 0);
  }
}

function startLivingSea() {
  window.AppState.isLivingSeaRunning = true;
  if (window.AppState.currentSimTimeMs === 0) {
    renderAtTime(0);
  }
  if (window.Logger) {
    window.Logger.log('PHYSICS', 'INFO', 'Инициализация гидродинамики судна и генератора волн/ветра.', null, 0);
  }
  playSimulation();
}

function stopLivingSeaToZero() {
  resetSimulation();
  if (window.Logger) {
    window.Logger.log('SIM_RUNNER', 'INFO', 'Симуляция остановлена (Стоп к нулю). Судно ошвартовано.', null, 0);
  }
}

function updateLivingSeaButtonState() {
  const btn = document.getElementById('btnLivingSeaToggle');
  const icon = document.getElementById('seaToggleIcon');
  const label = document.getElementById('seaToggleLabel');
  if (!btn) return;

  if (window.AppState.isPlaying) {
    btn.className = 'btn-living-sea-toggle state-running';
    if (icon) icon.textContent = '⏸';
    if (label) label.textContent = 'PAUSE SIMULATION';
  } else if (window.AppState.currentSimTimeMs > 0) {
    btn.className = 'btn-living-sea-toggle state-paused';
    if (icon) icon.textContent = '▶';
    if (label) label.textContent = 'RESUME SIMULATION (PLAY)';
  } else {
    btn.className = 'btn-living-sea-toggle state-stopped';
    if (icon) icon.textContent = '▶';
    if (label) label.textContent = 'START SIMULATION';
  }
}

function renderZeroState() {
  if (window.InstrumentRenderer) {
    window.InstrumentRenderer.reset();
  }

  const state = window.AppState;
  const durationMs = state.data ? state.data.duration_ms : state.durationS * 1000;
  let timeStr = durationMs >= 3600000 ? '00:00:00' : '00:00.00';
  const simTimeEl = document.getElementById('simTimeValue');
  if (simTimeEl) simTimeEl.textContent = timeStr;

  if (window.TimelineRenderer && state.data) {
    window.TimelineRenderer.updateCursor(0, state.data.duration_ms);
  }

  // Ground truth zeros
  const gtTws = document.getElementById('gtTws');
  if (gtTws) gtTws.innerHTML = `0.00 <span class="term-unit">kt</span>`;
  const gtTwd = document.getElementById('gtTwd');
  if (gtTwd) gtTwd.innerHTML = `000.0 <span class="term-unit">°</span>`;
  const gtWave = document.getElementById('gtWave');
  if (gtWave) gtWave.innerHTML = `0.00 <span class="term-unit">m</span>`;
  const gtHeave = document.getElementById('gtHeave');
  if (gtHeave) gtHeave.innerHTML = `0.00 <span class="term-unit">m</span>`;
  const gtSlamForce = document.getElementById('gtSlamForce');
  if (gtSlamForce) gtSlamForce.innerHTML = `0.0 <span class="term-unit">kN</span>`;
  const gtHeel = document.getElementById('gtHeel');
  if (gtHeel) gtHeel.innerHTML = `0.00 <span class="term-unit">°</span>`;
  const gtPitch = document.getElementById('gtPitch');
  if (gtPitch) gtPitch.innerHTML = `0.00 <span class="term-unit">°</span>`;
  const gtYaw = document.getElementById('gtYaw');
  if (gtYaw) gtYaw.innerHTML = `000.0 <span class="term-unit">°</span>`;
  const gtSog = document.getElementById('gtSog');
  if (gtSog) gtSog.innerHTML = `0.00 <span class="term-unit">kt</span>`;
  const gtRudder = document.getElementById('gtRudder');
  if (gtRudder) gtRudder.innerHTML = `0.0 <span class="term-unit">°</span>`;
  const gtHydroLoss = document.getElementById('gtHydroLoss');
  if (gtHydroLoss) gtHydroLoss.textContent = `0 %`;
  const gtActiveEvents = document.getElementById('gtActiveEvents');
  if (gtActiveEvents) gtActiveEvents.textContent = 'NONE';
  const gtStateTag = document.getElementById('gtStateTag');
  if (gtStateTag) {
    gtStateTag.textContent = 'STATUS: DOCKED';
    gtStateTag.style.color = '#94a3b8';
  }

  // Marine Dials Zeros
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

  // SailSteer B&G Zero State
  const sailSteerCanvas = document.getElementById('sailSteerCanvas');
  if (window.SailSteerRenderer) {
    window.SailSteerRenderer.renderZeroState(sailSteerCanvas);
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

  // Phase 12 Cockpit & Rig Control Zero State
  if (window.CockpitController && typeof window.CockpitController.update === 'function') {
    window.CockpitController.update({
      wind: { awa_deg: 40.0, aws_kt: 15.0 },
      helm: { rudder_deg: 0.0, command_deg: 0.0, hydro_loss: 0.0 }
    });
  }

  // SIA Advisory Panel at IDLE
  const siaHazardBadge = document.getElementById('siaHazardBadge');
  if (siaHazardBadge) {
    siaHazardBadge.className = 'hazard-badge nominal';
    siaHazardBadge.style.background = '';
    siaHazardBadge.style.color = '';
    siaHazardBadge.textContent = 'IDLE';
  }
  const siaRiskVal = document.getElementById('siaRiskVal');
  if (siaRiskVal) siaRiskVal.textContent = '0.00';
  const siaRiskBar = document.getElementById('siaRiskBar');
  if (siaRiskBar) siaRiskBar.style.width = '0%';
  const siaConfVal = document.getElementById('siaConfVal');
  if (siaConfVal) siaConfVal.textContent = '1.00';
  const siaConfBar = document.getElementById('siaConfBar');
  if (siaConfBar) siaConfBar.style.width = '100%';

  const primaryCardTag = document.getElementById('primaryCardTag');
  if (primaryCardTag) primaryCardTag.textContent = 'SYSTEM IDLE (PRESS START TO SAIL)';
  const primaryScore = document.getElementById('primaryScore');
  if (primaryScore) primaryScore.textContent = 'STATUS: IDLE';
  const primaryActionTitle = document.getElementById('primaryActionTitle');
  if (primaryActionTitle) primaryActionTitle.textContent = 'BOAT AT MOORINGS / STANDBY';
  const cmdRudder = document.getElementById('cmdRudder');
  if (cmdRudder) cmdRudder.textContent = '0.0°';
  const cmdSail = document.getElementById('cmdSail');
  if (cmdSail) cmdSail.textContent = '0%';
  const siaReasoningNote = document.getElementById('siaReasoningNote');
  if (siaReasoningNote) siaReasoningNote.textContent = 'Simulation stopped. Boat is stationary at moorings with all dials at zero.';

  const candList = document.getElementById('candidatesList');
  if (candList) candList.innerHTML = '<div class="candidate-row empty">Simulation stopped (Waiting for START)</div>';

  const queryCard = document.getElementById('zoneQueryLoop');
  const queryPrompt = document.getElementById('queryPromptText');
  if (queryCard) {
    queryCard.className = 'zone-card zone-query-loop-card standby';
  }
  if (queryPrompt) {
    queryPrompt.textContent = 'SIA Core: "Living sea standby. Continuous background telemetry monitoring active."';
  }
  document.querySelectorAll('.btn-query-chip').forEach(c => c.classList.remove('active'));

  const footerVerdict = document.getElementById('footerVerdict');
  if (footerVerdict) {
    footerVerdict.className = 'verdict-badge';
    footerVerdict.style.background = 'rgba(148, 163, 184, 0.15)';
    footerVerdict.style.color = '#94a3b8';
    footerVerdict.textContent = 'VERDICT: STANDBY';
  }
}

function renderAtTime(simTimeMs) {
  const state = window.AppState;
  if (!state.data) return;
  const interpState = getInterpolatedStateAtTime(simTimeMs);
  if (!interpState) return;

  const tA = interpState.tick;
  const tB = interpState.nextTick;
  const alpha = interpState.alpha;
  const activeTick = alpha < 0.5 ? tA : tB;

  // 1. Clock Display (Continuous 60 FPS update)
  const totalSeconds = Math.max(0, simTimeMs / 1000);
  let timeStr = '';
  if (state.data.duration_ms >= 3600000) {
    const hh = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
    const mm = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
    const ss = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
    timeStr = `${hh}:${mm}:${ss}`;
  } else {
    const mins = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const secs = (totalSeconds % 60).toFixed(2).padStart(5, '0');
    timeStr = `${mins}:${secs}`;
  }
  const simTimeEl = document.getElementById('simTimeValue');
  if (simTimeEl) simTimeEl.textContent = timeStr;

  // 2. Timeline Cursor
  if (window.TimelineRenderer) {
    window.TimelineRenderer.updateCursor(simTimeMs, state.data.duration_ms || 20000);
  }

  // 3. Zone 2: Ground Truth Lab Terminal
  const gtA = tA.ground_truth;
  const gtB = tB.ground_truth;
  const tws = lerp(gtA.tws_kt, gtB.tws_kt, alpha);
  const twd = lerpAngle(gtA.twd_deg, gtB.twd_deg, alpha);
  const waveElev = lerp(gtA.wave_elevation_m, gtB.wave_elevation_m, alpha);
  const heave = lerp(gtA.heave_m || 0.0, gtB.heave_m || 0.0, alpha);
  const slamForce = lerp(gtA.slam_force_kn || 0.0, gtB.slam_force_kn || 0.0, alpha);
  const heel = lerp(gtA.heel_deg, gtB.heel_deg, alpha);
  const pitch = lerp(gtA.pitch_deg || 0.0, gtB.pitch_deg || 0.0, alpha);
  const yaw = lerpAngle(gtA.yaw_deg, gtB.yaw_deg, alpha);
  const sog = lerp(gtA.sog_kt, gtB.sog_kt, alpha);
  const rudder = lerp(gtA.rudder_deg, gtB.rudder_deg, alpha);
  const hydroLoss = lerp(gtA.rudder_hydro_loss, gtB.rudder_hydro_loss, alpha);

  const gtTws = document.getElementById('gtTws');
  if (gtTws) gtTws.innerHTML = `${tws.toFixed(2)} <span class="term-unit">kt</span>`;
  const gtTwd = document.getElementById('gtTwd');
  if (gtTwd) gtTwd.innerHTML = `${twd.toFixed(1)} <span class="term-unit">°</span>`;
  const gtWave = document.getElementById('gtWave');
  if (gtWave) gtWave.innerHTML = `${waveElev.toFixed(2)} <span class="term-unit">m</span>`;
  const gtHeave = document.getElementById('gtHeave');
  if (gtHeave) gtHeave.innerHTML = `${heave.toFixed(2)} <span class="term-unit">m</span>`;
  const gtSlamForce = document.getElementById('gtSlamForce');
  if (gtSlamForce) gtSlamForce.innerHTML = `${slamForce.toFixed(1)} <span class="term-unit">kN</span>`;
  const gtHeel = document.getElementById('gtHeel');
  if (gtHeel) gtHeel.innerHTML = `${heel.toFixed(2)} <span class="term-unit">°</span>`;
  const gtPitch = document.getElementById('gtPitch');
  if (gtPitch) gtPitch.innerHTML = `${pitch.toFixed(2)} <span class="term-unit">°</span>`;
  const gtYaw = document.getElementById('gtYaw');
  if (gtYaw) gtYaw.innerHTML = `${yaw.toFixed(1)} <span class="term-unit">°</span>`;
  const gtSog = document.getElementById('gtSog');
  if (gtSog) gtSog.innerHTML = `${sog.toFixed(2)} <span class="term-unit">kt</span>`;
  const gtRudder = document.getElementById('gtRudder');
  if (gtRudder) gtRudder.innerHTML = `${rudder.toFixed(1)} <span class="term-unit">°</span>`;
  const gtHydroLoss = document.getElementById('gtHydroLoss');
  if (gtHydroLoss) gtHydroLoss.textContent = `${Math.round(hydroLoss * 100)} %`;
  
  const activeEvents = activeTick.ground_truth.active_events.length > 0
    ? activeTick.ground_truth.active_events.join(', ')
    : 'NONE';
  const gtActiveEvents = document.getElementById('gtActiveEvents');
  if (gtActiveEvents) gtActiveEvents.textContent = activeEvents;

  const gtStateTag = document.getElementById('gtStateTag');
  if (gtStateTag) {
    if (hydroLoss > 0.4) {
      gtStateTag.textContent = 'HYDRO: STALL';
      gtStateTag.style.color = '#ff1744';
    } else if (hydroLoss > 0.1) {
      gtStateTag.textContent = 'HYDRO: REDUCED LIFT';
      gtStateTag.style.color = '#ffb300';
    } else {
      gtStateTag.textContent = 'HYDRO: NOMINAL';
      gtStateTag.style.color = '#94a3b8';
    }
  }

  // 4. Zone 3: Sensor View (6 Marine Console Canvas Dials)
  const sfA = tA.sensor_frame;
  const sfB = tB.sensor_frame;
  const awa = lerpAngle(sfA.wind.apparent_wind_angle_deg, sfB.wind.apparent_wind_angle_deg, alpha);
  const aws = lerp(sfA.wind.apparent_wind_speed_kt, sfB.wind.apparent_wind_speed_kt, alpha);
  const imuRoll = lerp(sfA.imu.roll_deg, sfB.imu.roll_deg, alpha);
  const imuPitch = lerp(sfA.imu.pitch_deg, sfB.imu.pitch_deg, alpha);
  const imuPitchRate = lerp(sfA.imu.pitch_rate_deg_s, sfB.imu.pitch_rate_deg_s, alpha);
  const imuYawRate = lerp(sfA.imu.yaw_rate_deg_s, sfB.imu.yaw_rate_deg_s, alpha);
  const imuAccelZ = lerp(sfA.imu.accel_z_m_s2, sfB.imu.accel_z_m_s2, alpha);
  const gpsCog = lerpAngle(sfA.gps.cog_deg, sfB.gps.cog_deg, alpha);
  const gpsSog = lerp(sfA.gps.sog_kt, sfB.gps.sog_kt, alpha);
  const actRudder = lerp(sfA.actuators.rudder_angle_deg, sfB.actuators.rudder_angle_deg, alpha);
  const actSail = lerp(sfA.actuators.mainsheet_pct, sfB.actuators.mainsheet_pct, alpha);

  const windFault = activeTick.sensor_frame.wind.fault;
  const imuFault = activeTick.sensor_frame.imu.fault;
  const gpsFault = activeTick.sensor_frame.gps.fault || activeTick.sensor_frame.gps.fix_loss;

  const dialWindCanvas = document.getElementById('dialWindCanvas');
  const dialHeelCanvas = document.getElementById('dialHeelCanvas');
  const dialPitchCanvas = document.getElementById('dialPitchCanvas');
  const dialNavCanvas = document.getElementById('dialNavCanvas');
  const dialHeaveCanvas = document.getElementById('dialHeaveCanvas');
  const dialSlamCanvas = document.getElementById('dialSlamCanvas');

  if (dialWindCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawWindDial(
      dialWindCanvas,
      awa !== null ? awa : 0.0,
      aws !== null ? aws : 0.0,
      windFault
    );
  }
  const valAws = document.getElementById('valAws');
  if (valAws) {
    valAws.innerHTML = aws !== null
      ? `${aws.toFixed(1)} <span class="unit">kt</span>`
      : `--- <span class="unit">NO SIGNAL</span>`;
  }

  if (dialHeelCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawHeelDial(
      dialHeelCanvas,
      imuRoll !== null ? imuRoll : 0.0,
      imuFault
    );
  }
  const valHeel = document.getElementById('valHeel');
  if (valHeel) {
    valHeel.innerHTML = imuRoll !== null
      ? `${imuRoll.toFixed(1)} <span class="unit">°</span>`
      : `--- <span class="unit">NO FIX</span>`;
  }

  if (dialPitchCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawPitchDial(
      dialPitchCanvas,
      imuPitch !== null ? imuPitch : 0.0,
      imuPitchRate !== null ? imuPitchRate : 0.0,
      imuFault
    );
  }
  const valPitchEl = document.getElementById('valPitch');
  if (valPitchEl) {
    valPitchEl.innerHTML = imuPitch !== null
      ? `${imuPitch.toFixed(1)} <span class="unit">°</span>`
      : `--- <span class="unit">NO FIX</span>`;
  }

  if (dialNavCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawNavDial(
      dialNavCanvas,
      gpsCog !== null ? gpsCog : 0.0,
      gpsSog !== null ? gpsSog : 0.0,
      gpsFault
    );
  }
  const valSog = document.getElementById('valSog');
  if (valSog) {
    valSog.innerHTML = gpsSog !== null
      ? `${gpsSog.toFixed(1)} <span class="unit">kt</span>`
      : `--- <span class="unit">NO FIX</span>`;
  }

  if (dialHeaveCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawHeaveGauge(
      dialHeaveCanvas,
      heave,
      imuAccelZ !== null ? imuAccelZ : 9.81,
      imuFault
    );
  }
  const valHeaveEl = document.getElementById('valHeaveAccel');
  if (valHeaveEl) {
    const gVal = imuAccelZ !== null ? (imuAccelZ / 9.80665).toFixed(2) : '1.00';
    valHeaveEl.innerHTML = imuAccelZ !== null
      ? `${gVal} <span class="unit">g</span>`
      : `--- <span class="unit">NO FIX</span>`;
  }

  const isSlamming = activeTick.ground_truth.slam_active || slamForce > 5.0;
  if (dialSlamCanvas && window.InstrumentRenderer) {
    InstrumentRenderer.drawSlammingGauge(
      dialSlamCanvas,
      slamForce,
      isSlamming,
      15.0,
      imuFault
    );
  }
  const cardSlam = document.getElementById('cardSlamming');
  if (cardSlam) {
    cardSlam.classList.toggle('slam-active', isSlamming);
  }
  const valSlamEl = document.getElementById('valSlamForce');
  if (valSlamEl) {
    valSlamEl.innerHTML = `${slamForce.toFixed(1)} <span class="unit">kN</span>`;
  }

  const valPitchRate = document.getElementById('valPitchRate');
  if (valPitchRate) valPitchRate.textContent = imuPitchRate !== null ? `${imuPitchRate.toFixed(1)} °/s` : '---';
  const valYawRate = document.getElementById('valYawRate');
  if (valYawRate) valYawRate.textContent = imuYawRate !== null ? `${imuYawRate.toFixed(1)} °/s` : '---';
  const valRudderSensor = document.getElementById('valRudderSensor');
  if (valRudderSensor) valRudderSensor.textContent = actRudder !== null ? `${actRudder.toFixed(1)} °` : '---';
  const valSailSensor = document.getElementById('valSailSensor');
  if (valSailSensor) valSailSensor.textContent = actSail !== null ? `${actSail.toFixed(0)} %` : 'UNKNOWN (ABSENT)';

  const chipImu = document.getElementById('chipImu');
  if (chipImu) {
    chipImu.className = activeTick.sensor_frame.imu.fault ? 'health-chip chip-fault' : 'health-chip chip-ok';
    chipImu.textContent = activeTick.sensor_frame.imu.fault ? 'IMU: FAULT' : 'IMU: OK';
  }
  const chipGps = document.getElementById('chipGps');
  if (chipGps) {
    chipGps.className = gpsFault ? 'health-chip chip-fault' : 'health-chip chip-ok';
    chipGps.textContent = activeTick.sensor_frame.gps.fault ? 'GPS: FAULT' : (activeTick.sensor_frame.gps.fix_loss ? 'GPS: NO FIX' : 'GPS: OK');
  }
  const chipWind = document.getElementById('chipWind');
  if (chipWind) {
    chipWind.className = activeTick.sensor_frame.wind.fault ? 'health-chip chip-fault' : 'health-chip chip-ok';
    chipWind.textContent = activeTick.sensor_frame.wind.fault ? 'WIND: FAULT' : 'WIND: OK';
  }

  // Phase 12 Cockpit & Rig Control Live Wind & Helm Update
  if (window.CockpitController && typeof window.CockpitController.update === 'function') {
    window.CockpitController.update({
      wind: {
        awa_deg: awa !== null ? awa : 40.0,
        aws_kt: aws !== null ? aws : 15.0,
      },
      helm: {
        rudder_deg: rudder !== null ? rudder : (actRudder !== null ? actRudder : 0.0),
        command_deg: sel.rudder_command_deg !== null ? sel.rudder_command_deg : (actRudder !== null ? actRudder : 0.0),
        hydro_loss: hydroLoss !== null ? hydroLoss : 0.0,
      }
    });
  }

  // B&G SailSteer™ Navigation Display Render

  const sailSteerCanvas = document.getElementById('sailSteerCanvas');
  if (sailSteerCanvas && window.SailSteerRenderer && window.SailSteerController) {
    const rawTick = {
      sim_time_ms: simTimeMs,
      ground_truth: {
        tws_kt: tws,
        twd_deg: twd,
        wave_elevation_m: waveElev,
        heave_m: heave,
        slam_force_kn: slamForce,
        heel_deg: heel,
        pitch_deg: pitch,
        yaw_deg: yaw,
        sog_kt: sog,
        rudder_deg: rudder,
        current_speed_kt: 1.2,
        current_dir_deg: 135.0,
      },
      sensor_frame: {
        imu: {
          roll_deg: imuRoll,
          pitch_deg: imuPitch,
          pitch_rate_deg_s: imuPitchRate,
          yaw_rate_deg_s: imuYawRate,
          accel_z_m_s2: imuAccelZ,
          fault: imuFault,
        },
        gps: {
          sog_kt: gpsSog,
          cog_deg: gpsCog,
          latitude_deg: 42.25528,
          longitude_deg: 17.97368,
          fault: gpsFault,
          fix_loss: gpsFault,
        },
        wind: {
          apparent_wind_speed_kt: aws,
          apparent_wind_angle_deg: awa,
          fault: windFault,
        },
        actuators: {
          rudder_angle_deg: actRudder,
          mainsheet_pct: actSail,
        },
      },
    };
    const ssTelemetry = SailSteerController.process(rawTick);
    SailSteerRenderer.render(sailSteerCanvas, ssTelemetry);
  }

  // 5. Zone 4: SIA Advisory & Reasoning
  const sia = activeTick.sia_decision;
  const siaHazardBadge = document.getElementById('siaHazardBadge');
  if (siaHazardBadge) {
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
  }

  const siaRiskVal = document.getElementById('siaRiskVal');
  if (siaRiskVal) siaRiskVal.textContent = sia.risk_score.toFixed(2);
  const siaRiskBar = document.getElementById('siaRiskBar');
  if (siaRiskBar) siaRiskBar.style.width = `${Math.min(100, sia.risk_score * 100)}%`;
  const siaConfVal = document.getElementById('siaConfVal');
  if (siaConfVal) siaConfVal.textContent = sia.confidence.toFixed(2);
  const siaConfBar = document.getElementById('siaConfBar');
  if (siaConfBar) siaConfBar.style.width = `${Math.min(100, sia.confidence * 100)}%`;

  const sel = sia.selected_response;
  const primaryCardTag = document.getElementById('primaryCardTag');

  if (sel) {
    if (primaryCardTag) primaryCardTag.textContent = 'PRIMARY RECOMMENDED ACTION (HAZARD ACTIVE)';
    const primaryScore = document.getElementById('primaryScore');
    if (primaryScore) primaryScore.textContent = `SCORE: ${sel.priority_score.toFixed(2)}`;
    const primaryActionTitle = document.getElementById('primaryActionTitle');
    if (primaryActionTitle) primaryActionTitle.textContent = sel.action_type.replace(/_/g, ' ');
    const cmdRudder = document.getElementById('cmdRudder');
    if (cmdRudder) cmdRudder.textContent = sel.rudder_command_deg !== null ? `${sel.rudder_command_deg.toFixed(1)}°` : 'NONE';
    const cmdSail = document.getElementById('cmdSail');
    if (cmdSail) cmdSail.textContent = sel.sail_command_pct !== null ? `${sel.sail_command_pct.toFixed(0)}%` : 'MAINTAIN';
  } else {
    if (primaryCardTag) primaryCardTag.textContent = 'CONTINUOUS SAFETY MONITORING (NOMINAL)';
    const primaryScore = document.getElementById('primaryScore');
    if (primaryScore) primaryScore.textContent = 'STATUS: SAFE';
    const primaryActionTitle = document.getElementById('primaryActionTitle');
    if (primaryActionTitle) primaryActionTitle.textContent = 'MAINTAIN COURSE & MONITOR TRIM';
    const cmdRudder = document.getElementById('cmdRudder');
    if (cmdRudder) cmdRudder.textContent = '0.0°';
    const cmdSail = document.getElementById('cmdSail');
    if (cmdSail) cmdSail.textContent = '100%';
  }

  const candList = document.getElementById('candidatesList');
  if (candList) {
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
  }

  const siaReasoningNote = document.getElementById('siaReasoningNote');
  if (siaReasoningNote) siaReasoningNote.textContent = sia.note || 'Nominal monitoring active';

  // 6. Footer Evaluator Status
  const evalData = state.data.evaluation;
  const footerEnvelope = document.getElementById('footerEnvelope');
  const oracle = activeTick.oracle;

  if (footerEnvelope) {
    if (oracle.safe_envelope_intact) {
      footerEnvelope.className = 'footer-val val-pass';
      footerEnvelope.textContent = `INTACT (Margin: ${oracle.safety_margin_pct}%)`;
    } else {
      footerEnvelope.className = 'footer-val highlight-danger';
      footerEnvelope.textContent = 'BREACHED (>35° KNOCKDOWN)';
    }
  }

  const footerLatency = document.getElementById('footerLatency');
  if (footerLatency) {
    if (evalData.detection_latency_ms !== null) {
      footerLatency.textContent = `${evalData.detection_latency_ms} ms (Target < 500 ms)`;
    } else {
      footerLatency.textContent = 'N/A (No Hazard)';
    }
  }

  const footerFalseAlarms = document.getElementById('footerFalseAlarms');
  if (footerFalseAlarms) {
    footerFalseAlarms.textContent = evalData.false_positives.toString();
  }
  
  const footerVerdict = document.getElementById('footerVerdict');
  if (footerVerdict) {
    footerVerdict.className = evalData.verdict === 'PASS' ? 'verdict-badge badge-pass' : 'verdict-badge badge-fail';
    footerVerdict.textContent = `VERDICT: ${evalData.verdict} (M6)`;
  }

  // 7. Dynamic Query Loop Display
  if (window.updateQueryLoopDisplay) {
    window.updateQueryLoopDisplay(activeTick);
  }
}

function renderTick(index) {
  const state = window.AppState;
  if (!state.data || !state.data.ticks || !state.data.ticks[index]) return;
  const tick = state.data.ticks[index];
  state.currentSimTimeMs = tick.sim_time_ms;
  renderAtTime(tick.sim_time_ms);
}

window.PlaybackController = {
  lerp,
  lerpAngle,
  getInterpolatedStateAtTime,
  playSimulation,
  pauseSimulation,
  stepSimulation,
  resetSimulation,
  startLivingSea,
  stopLivingSeaToZero,
  updateLivingSeaButtonState,
  renderZeroState,
  renderAtTime,
  renderTick,
};

window.playSimulation = playSimulation;
window.pauseSimulation = pauseSimulation;
window.stepSimulation = stepSimulation;
window.resetSimulation = resetSimulation;
window.startLivingSea = startLivingSea;
window.stopLivingSeaToZero = stopLivingSeaToZero;
window.renderAtTime = renderAtTime;
window.renderTick = renderTick;
window.renderZeroState = renderZeroState;
