/**
 * Skipper-in-the-Loop Interactive Query Loop (Dynamic State Engine)
 */

window.userConfirmedSail = null;

document.addEventListener('DOMContentLoaded', () => {
  initQueryLoop();
});

function initQueryLoop() {
  const queryChips = document.querySelectorAll('.btn-query-chip');
  queryChips.forEach((chip) => {
    chip.addEventListener('click', async (e) => {
      const sailSet = e.currentTarget.getAttribute('data-sail');
      window.userConfirmedSail = sailSet;
      
      // Update UI active state
      queryChips.forEach((c) => c.classList.remove('active'));
      e.currentTarget.classList.add('active');

      await dispatchSkipperAction(sailSet);
    });
  });
}

function updateQueryLoopDisplay(tick) {
  const cardEl = document.getElementById('zoneQueryLoop');
  const titleEl = cardEl ? cardEl.querySelector('.query-title') : null;
  const iconEl = cardEl ? cardEl.querySelector('.query-prompt-icon') : null;
  const promptEl = document.getElementById('queryPromptText');
  const queryChips = document.querySelectorAll('.btn-query-chip');

  if (!cardEl || !titleEl || !promptEl) return;

  const sf = tick.sensor_frame;
  const sia = tick.sia_decision;
  const gt = tick.ground_truth;
  const roll = Math.abs(sf.imu.roll_deg || 0);
  const isHazard = sia.risk_score >= 0.35 || sia.hazard_id !== null || roll >= 18.0 || gt.slam_active;

  if (window.userConfirmedSail) {
    // State 3: User responded and confirmed sail state
    cardEl.className = 'zone-card zone-query-loop-card confirmed';
    if (iconEl) iconEl.textContent = '✅';
    titleEl.textContent = `CONTEXT CONFIRMED: ${window.userConfirmedSail.replace(/_/g, ' ')}`;
    promptEl.textContent = `SIA Core: "Confirmed sail configuration: [${window.userConfirmedSail.replace(/_/g, ' ')}]. Advisory priorities recalculated."`;
    queryChips.forEach(c => {
      c.classList.toggle('active', c.getAttribute('data-sail') === window.userConfirmedSail);
    });
  } else if (isHazard) {
    // State 2: Anomaly / Hazard active -> SIA needs human clarification
    cardEl.className = 'zone-card zone-query-loop-card active-query';
    if (iconEl) iconEl.textContent = '💡';
    titleEl.textContent = '💡 SKIPPER QUERY: CONTEXT REFINEMENT REQUIRED';
    promptEl.textContent = `SIA Core: "Dynamic heel (${roll.toFixed(1)}°) & hazard detected. Confirm active sail rig to refine counter-action:"`;
    queryChips.forEach(c => c.classList.remove('active'));
  } else {
    // State 1: Nominal cruising -> Query Loop is in STANDBY
    cardEl.className = 'zone-card zone-query-loop-card standby';
    if (iconEl) iconEl.textContent = '🛡️';
    titleEl.textContent = 'SKIPPER QUERY LOOP (STANDBY)';
    promptEl.textContent = 'SIA Core: "Telemetry nominal. Continuous background monitoring active. No context query needed."';
    queryChips.forEach(c => c.classList.remove('active'));
  }
}

async function dispatchSkipperAction(sailSet) {
  const simTimeMs = window.AppState ? (window.AppState.currentSimTimeMs || 0) : 0;
  
  try {
    const res = await fetch('/api/query-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sail_set: sailSet,
        sim_time_ms: Math.round(simTimeMs),
      }),
    });
    const result = await res.json();

    if (result.status === 'recalculated') {
      // Update Zone 4 with recalculated decision candidates
      const candList = document.getElementById('candidatesList');
      if (candList && result.candidates) {
        candList.innerHTML = '';
        result.candidates.slice(0, 3).forEach((c, idx) => {
          const row = document.createElement('div');
          row.className = 'candidate-row';
          row.innerHTML = `
            <span class="cand-name">${idx + 1}. ${c.action_type.replace(/_/g, ' ')}</span>
            <span class="cand-score">Score: ${c.priority_score.toFixed(2)}</span>
          `;
          candList.appendChild(row);
        });
      }

      // Update primary card
      const sel = result.selected_response;
      if (sel) {
        document.getElementById('primaryScore').textContent = `SCORE: ${sel.priority_score.toFixed(2)}`;
        document.getElementById('primaryActionTitle').textContent = sel.action_type.replace(/_/g, ' ');
        document.getElementById('cmdRudder').textContent = sel.rudder_command_deg !== null ? `${sel.rudder_command_deg.toFixed(1)}°` : 'NONE';
        document.getElementById('cmdSail').textContent = sel.sail_command_pct !== null ? `${sel.sail_command_pct.toFixed(0)}%` : 'MAINTAIN';
      }

      // Update reasoning note
      document.getElementById('siaReasoningNote').textContent = result.note;

      // Update Query Loop display
      if (window.renderAtTime && window.AppState) {
        window.renderAtTime(window.AppState.currentSimTimeMs || 0);
      }
    }
  } catch (err) {
    console.error('Failed to dispatch skipper query action:', err);
  }
}

window.updateQueryLoopDisplay = updateQueryLoopDisplay;
