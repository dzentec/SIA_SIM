/**
 * Skipper-in-the-Loop Interactive Query Loop (Zone 5)
 */

document.addEventListener('DOMContentLoaded', () => {
  initQueryLoop();
});

function initQueryLoop() {
  const queryChips = document.querySelectorAll('.btn-query-chip');
  queryChips.forEach((chip) => {
    chip.addEventListener('click', async (e) => {
      const sailSet = e.currentTarget.getAttribute('data-sail');
      
      // Update UI active state
      queryChips.forEach((c) => c.classList.remove('active'));
      e.currentTarget.classList.add('active');

      await dispatchSkipperAction(sailSet);
    });
  });
}

async function dispatchSkipperAction(sailSet) {
  const simTimeMs = window.AppState ? window.AppState.currentTick * 10 : 0;
  
  try {
    const res = await fetch('/api/query-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sail_set: sailSet,
        sim_time_ms: simTimeMs,
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
    }
  } catch (err) {
    console.error('Failed to dispatch skipper query action:', err);
  }
}
