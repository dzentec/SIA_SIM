/**
 * Skipper-in-the-Loop Interactive Query Loop (Dynamic State Engine)
 */

window.userConfirmedSail = null;
window.queryActiveUntilMs = 0;
window.queryTriggeredAtMs = 0;
const QUERY_DURATION_MS = 10000; // 10 seconds timeout for skipper response

document.addEventListener('DOMContentLoaded', () => {
  initQueryLoop();
});

function initQueryLoop() {
  const queryChips = document.querySelectorAll('.btn-query-chip');
  queryChips.forEach((chip) => {
    chip.addEventListener('click', async (e) => {
      const sailSet = e.currentTarget.getAttribute('data-sail');
      window.userConfirmedSail = sailSet;
      window.queryActiveUntilMs = 0;
      
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
  const badgeEl = document.getElementById('queryCountdownBadge');
  const barContainerEl = document.getElementById('queryTimerBarContainer');
  const barFillEl = document.getElementById('queryTimerBarFill');
  const queryChips = document.querySelectorAll('.btn-query-chip');

  if (!cardEl || !titleEl || !promptEl) return;

  const simTimeMs = tick.sim_time_ms || 0;
  const sf = tick.sensor_frame;
  const sia = tick.sia_decision;
  const gt = tick.ground_truth;
  const roll = Math.abs(sf.imu.roll_deg || 0);
  const isHazard = sia.risk_score >= 0.35 || sia.hazard_id !== null || roll >= 18.0 || (gt && gt.slam_active);

  // If user reset or scrubbed back before trigger time, reset query state
  if (window.queryTriggeredAtMs && simTimeMs < window.queryTriggeredAtMs) {
    window.queryActiveUntilMs = 0;
    window.queryTriggeredAtMs = 0;
    window.userConfirmedSail = null;
  }

  // Check if hazard triggers a new 10s query latch
  if (isHazard && !window.userConfirmedSail) {
    if (!window.queryActiveUntilMs || simTimeMs > window.queryActiveUntilMs) {
      window.queryTriggeredAtMs = simTimeMs;
      window.queryActiveUntilMs = simTimeMs + QUERY_DURATION_MS;
    }
  }

  const isQueryActive = window.queryActiveUntilMs && (simTimeMs <= window.queryActiveUntilMs) && !window.userConfirmedSail;

  if (window.userConfirmedSail) {
    // State 3: User responded and confirmed sail state
    cardEl.className = 'zone-card zone-query-loop-card confirmed';
    if (iconEl) iconEl.textContent = '✅';
    if (badgeEl) badgeEl.style.display = 'none';
    if (barContainerEl) barContainerEl.style.display = 'none';
    titleEl.textContent = `CONTEXT CONFIRMED: ${window.userConfirmedSail.replace(/_/g, ' ')}`;
    promptEl.textContent = `SIA Core: "Confirmed sail configuration: [${window.userConfirmedSail.replace(/_/g, ' ')}]. Advisory priorities recalculated."`;
    queryChips.forEach(c => {
      c.classList.toggle('active', c.getAttribute('data-sail') === window.userConfirmedSail);
    });
  } else if (isQueryActive) {
    // State 2: LATCHED 10-second active query with countdown timer & progress bar
    const remainingMs = Math.max(0, window.queryActiveUntilMs - simTimeMs);
    const remainingSec = (remainingMs / 1000).toFixed(1);
    const progressPct = Math.max(0, Math.min(100, (remainingMs / QUERY_DURATION_MS) * 100));

    cardEl.className = 'zone-card zone-query-loop-card active-query';
    if (iconEl) iconEl.textContent = '💡';
    
    // Countdown badge
    if (badgeEl) {
      badgeEl.style.display = 'inline-block';
      badgeEl.textContent = `⏱ ${remainingSec}s`;
      badgeEl.style.color = '#ffb703';
      badgeEl.style.borderColor = 'rgba(255, 183, 3, 0.4)';
      badgeEl.style.background = 'rgba(255, 183, 3, 0.15)';
    }

    // Countdown progress bar
    if (barContainerEl && barFillEl) {
      barContainerEl.style.display = 'block';
      barFillEl.style.width = `${progressPct}%`;
      if (progressPct < 30) {
        barFillEl.style.background = '#ef4444';
      } else {
        barFillEl.style.background = 'linear-gradient(90deg, #ffb703, #ef4444)';
      }
    }

    titleEl.textContent = `💡 SKIPPER QUERY: CONFIRM SAIL PLAN (⏱ ${remainingSec}s)`;
    promptEl.textContent = `SIA Core: "Dynamic heel (${roll.toFixed(1)}°) & hazard detected. Confirm active sail rig [⏱ ${remainingSec}s remaining]:"`;
    queryChips.forEach(c => c.classList.remove('active'));
  } else if (window.queryActiveUntilMs && simTimeMs > window.queryActiveUntilMs && (simTimeMs - window.queryActiveUntilMs < 4000)) {
    // State 2.5: Brief timeout notice for 4 seconds after expiration
    cardEl.className = 'zone-card zone-query-loop-card standby';
    if (iconEl) iconEl.textContent = '⏳';
    if (badgeEl) {
      badgeEl.style.display = 'inline-block';
      badgeEl.textContent = 'TIMEOUT';
      badgeEl.style.color = '#ef4444';
      badgeEl.style.borderColor = 'rgba(239, 68, 68, 0.4)';
      badgeEl.style.background = 'rgba(239, 68, 68, 0.15)';
    }
    if (barContainerEl) barContainerEl.style.display = 'none';
    titleEl.textContent = '⏳ SKIPPER QUERY TIMED OUT';
    promptEl.textContent = 'SIA Core: "No skipper response within 10s window. Defaulted to conservative safety protocol."';
    queryChips.forEach(c => c.classList.remove('active'));
  } else {
    // State 1: Nominal cruising -> Query Loop is in STANDBY
    cardEl.className = 'zone-card zone-query-loop-card standby';
    if (iconEl) iconEl.textContent = '🛡️';
    if (badgeEl) badgeEl.style.display = 'none';
    if (barContainerEl) barContainerEl.style.display = 'none';
    titleEl.textContent = 'SKIPPER QUERY LOOP (STANDBY)';
    promptEl.textContent = 'SIA Core: "Living sea standby. Continuous background telemetry monitoring active. No context query needed."';
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
