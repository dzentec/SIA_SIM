/**
 * Skipper-in-the-Loop Interactive Query Loop (Active Sensing & Wardrobe Engine)
 *
 * 1. SIA Core knows only the vessel's sail wardrobe (available_sails).
 * 2. SIA has no sensors on sheets/halyards, so it inquires the skipper during hazards.
 * 3. On inquiry: Simulation auto-pauses (without timer countdown).
 * 4. Skipper selects sails & reefs in 2-column layout and submits to SIA.
 * 5. SIA recalculates advice, and simulation resumes seamlessly on Play.
 */

const SAIL_CONFIG_CATALOG = {
  mainsail_square_top: {
    id: 'mainsail_square_top',
    name: 'Грот (Square-Top)',
    category: 'Main',
    settings: [
      { id: 'FULL', label: '⛵ Полный (100%)', scale: 1.0, preset: 'FULL_MAIN', tag: 'Full' },
      { id: 'REEF_1', label: '📉 Риф 1 (75%)', scale: 0.75, preset: 'REEF_1', tag: 'Риф 1' },
      { id: 'REEF_2', label: '📉 Риф 2 (55%)', scale: 0.55, preset: 'REEF_2', tag: 'Риф 2' },
      { id: 'REEF_3', label: '📉 Риф 3 (35%)', scale: 0.35, preset: 'REEF_3', tag: 'Риф 3' },
      { id: 'BARE', label: '⚙ Убран (0%)', scale: 0.0, preset: 'BARE_POLES', tag: 'Убран' },
    ],
  },
  mainsail: {
    id: 'mainsail',
    name: 'Грот (Classic Main)',
    category: 'Main',
    settings: [
      { id: 'FULL', label: '⛵ Полный (100%)', scale: 1.0, preset: 'FULL_MAIN', tag: 'Full' },
      { id: 'REEF_1', label: '📉 Риф 1 (75%)', scale: 0.75, preset: 'REEF_1', tag: 'Риф 1' },
      { id: 'REEF_2', label: '📉 Риф 2 (55%)', scale: 0.55, preset: 'REEF_2', tag: 'Риф 2' },
      { id: 'REEF_3', label: '📉 Риф 3 (35%)', scale: 0.35, preset: 'REEF_3', tag: 'Риф 3' },
      { id: 'BARE', label: '⚙ Убран (0%)', scale: 0.0, preset: 'BARE_POLES', tag: 'Убран' },
    ],
  },
  genoa_furling: {
    id: 'genoa_furling',
    name: 'Генуя (Genoa 140%)',
    category: 'Headsail',
    settings: [
      { id: 'FULL', label: '100% (Развернута)', scale: 1.0, preset: 'FULL_MAIN', tag: '100%' },
      { id: 'REEF_1', label: '70% (Подкручена)', scale: 0.70, preset: 'REEF_1', tag: '70%' },
      { id: 'REEF_2', label: '40% (Скручена)', scale: 0.40, preset: 'REEF_2', tag: '40%' },
      { id: 'FURLED', label: 'Скручена (0%)', scale: 0.0, preset: 'BARE_POLES', tag: 'Скручена' },
    ],
  },
  solent_jib: {
    id: 'solent_jib',
    name: 'Солент-стаксель (Solent)',
    category: 'Headsail',
    settings: [
      { id: 'FULL', label: '100% (Поднят)', scale: 1.0, preset: 'FULL_MAIN', tag: '100%' },
      { id: 'REEF_1', label: '50% (Подкручен)', scale: 0.50, preset: 'REEF_1', tag: '50%' },
      { id: 'FURLED', label: 'Скручен (0%)', scale: 0.0, preset: 'BARE_POLES', tag: 'Скручен' },
    ],
  },
  code_zero: {
    id: 'code_zero',
    name: 'Code 0 (Крыло/Курс)',
    category: 'Downwind',
    settings: [
      { id: 'HOISTED', label: '⚡ Поднят (100%)', scale: 1.0, preset: 'CODE_ZERO', tag: 'Поднят' },
      { id: 'FURLED', label: 'Закручен (0%)', scale: 0.0, preset: 'FULL_MAIN', tag: 'Закручен' },
    ],
  },
  asymmetric_gennaker_a2: {
    id: 'asymmetric_gennaker_a2',
    name: 'Геннакер A2',
    category: 'Downwind',
    settings: [
      { id: 'HOISTED', label: '🎈 Несем (100%)', scale: 1.0, preset: 'GENNAKER', tag: 'Несем' },
      { id: 'FURLED', label: 'В чулке / Убран', scale: 0.0, preset: 'FULL_MAIN', tag: 'В чулке' },
    ],
  },
  parasailor: {
    id: 'parasailor',
    name: 'Parasailor',
    category: 'Downwind',
    settings: [
      { id: 'HOISTED', label: '🪂 Поднят (100%)', scale: 1.0, preset: 'GENNAKER', tag: 'Поднят' },
      { id: 'FURLED', label: 'Убран (0%)', scale: 0.0, preset: 'FULL_MAIN', tag: 'Убран' },
    ],
  },
  storm_jib: {
    id: 'storm_jib',
    name: 'Штормовой стаксель',
    category: 'Storm',
    settings: [
      { id: 'HOISTED', label: '⛈ Поднят (100%)', scale: 1.0, preset: 'STORM_JIB', tag: 'Поднят' },
      { id: 'FURLED', label: 'Убран (0%)', scale: 0.0, preset: 'BARE_POLES', tag: 'Убран' },
    ],
  },
};

window.QueryLoopState = {
  focusedSailId: 'mainsail_square_top',
  activeWardrobeConfig: {
    mainsail_square_top: 'FULL',
    genoa_furling: 'FULL',
  },
  isQueryActive: false,
  isConfirmed: false,
  confirmedSummary: '',
  lastTriggeredSimTimeMs: null,
};

document.addEventListener('DOMContentLoaded', () => {
  initQueryLoop();
});

function initQueryLoop() {
  const btnConfirm = document.getElementById('btnConfirmQuery');
  if (btnConfirm) {
    btnConfirm.addEventListener('click', async () => {
      await submitSkipperSailConfiguration();
    });
  }
  renderQueryWardrobe();
}

function getAvailableSailsList() {
  if (window.AppState && window.AppState.customVessel && window.AppState.customVessel.available_sails) {
    return window.AppState.customVessel.available_sails;
  }
  if (window.AppState && window.AppState.vesselPreset === 'monohull_ior') {
    return ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'storm_jib'];
  }
  return ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'code_zero', 'asymmetric_gennaker_a2', 'storm_jib'];
}

function renderQueryWardrobe() {
  const sailsListEl = document.getElementById('querySailsList');
  const settingsListEl = document.getElementById('querySettingsList');
  const summaryValEl = document.getElementById('querySummaryVal');
  if (!sailsListEl || !settingsListEl) return;

  const avail = getAvailableSailsList();
  const qState = window.QueryLoopState;

  // Validate focused sail
  if (!avail.includes(qState.focusedSailId)) {
    qState.focusedSailId = avail[0] || 'mainsail_square_top';
  }

  // Ensure default configurations
  avail.forEach(sailId => {
    if (!qState.activeWardrobeConfig[sailId]) {
      if (sailId.includes('main')) qState.activeWardrobeConfig[sailId] = 'FULL';
      else if (sailId.includes('genoa') || sailId.includes('solent')) qState.activeWardrobeConfig[sailId] = 'FULL';
      else qState.activeWardrobeConfig[sailId] = 'FURLED';
    }
  });

  // 1. Render Column 1: Sails
  sailsListEl.innerHTML = '';
  avail.forEach(sailId => {
    const sailDef = SAIL_CONFIG_CATALOG[sailId] || {
      id: sailId,
      name: sailId.replace(/_/g, ' '),
      settings: [
        { id: 'HOISTED', label: 'Поднят (100%)', scale: 1.0, preset: 'FULL_MAIN', tag: '100%' },
        { id: 'FURLED', label: 'Убран (0%)', scale: 0.0, preset: 'BARE_POLES', tag: '0%' },
      ],
    };

    const currentSettingId = qState.activeWardrobeConfig[sailId] || 'FURLED';
    const currentSetting = sailDef.settings.find(s => s.id === currentSettingId) || sailDef.settings[0];
    const isFocused = qState.focusedSailId === sailId;
    const isCarrying = currentSetting && currentSetting.scale > 0;

    const btn = document.createElement('button');
    btn.className = `btn-wardrobe-sail${isFocused ? ' focused' : ''}${isCarrying ? ' active-rig' : ''}`;
    btn.innerHTML = `
      <span>${sailDef.name}</span>
      <span class="sail-tag">${currentSetting ? currentSetting.tag : 'Off'}</span>
    `;

    btn.addEventListener('click', () => {
      qState.focusedSailId = sailId;
      renderQueryWardrobe();
    });

    sailsListEl.appendChild(btn);
  });

  // 2. Render Column 2: Settings for Focused Sail
  settingsListEl.innerHTML = '';
  const focusedDef = SAIL_CONFIG_CATALOG[qState.focusedSailId] || {
    id: qState.focusedSailId,
    name: qState.focusedSailId.replace(/_/g, ' '),
    settings: [
      { id: 'HOISTED', label: 'Поднят (100%)', scale: 1.0, preset: 'FULL_MAIN', tag: '100%' },
      { id: 'FURLED', label: 'Убран (0%)', scale: 0.0, preset: 'BARE_POLES', tag: '0%' },
    ],
  };

  const activeSettingId = qState.activeWardrobeConfig[qState.focusedSailId] || 'FULL';

  focusedDef.settings.forEach(setting => {
    const isSelected = activeSettingId === setting.id;
    const sBtn = document.createElement('button');
    sBtn.className = `btn-wardrobe-setting${isSelected ? ' selected' : ''}`;
    sBtn.innerHTML = `
      <span>${setting.label}</span>
      <span>${isSelected ? '●' : '○'}</span>
    `;

    sBtn.addEventListener('click', () => {
      qState.activeWardrobeConfig[qState.focusedSailId] = setting.id;
      syncWithActiveRigDeck();
      renderQueryWardrobe();
    });

    settingsListEl.appendChild(sBtn);
  });

  // 3. Update Summary text
  if (summaryValEl) {
    const activeParts = [];
    avail.forEach(sailId => {
      const sId = qState.activeWardrobeConfig[sailId];
      const sDef = SAIL_CONFIG_CATALOG[sailId];
      if (sDef) {
        const setObj = sDef.settings.find(s => s.id === sId);
        if (setObj && setObj.scale > 0) {
          activeParts.push(`${sDef.name.split(' ')[0]} (${setObj.tag})`);
        }
      }
    });
    summaryValEl.textContent = activeParts.length > 0 ? activeParts.join(' + ') : 'Без парусов (Bare Poles)';
  }
}

function syncWithActiveRigDeck() {
  if (!window.AppState) return;
  const qState = window.QueryLoopState;
  const activeSailsMap = {};

  Object.entries(qState.activeWardrobeConfig).forEach(([sailId, settingId]) => {
    const sDef = SAIL_CONFIG_CATALOG[sailId];
    if (sDef) {
      const setObj = sDef.settings.find(s => s.id === settingId);
      if (setObj && setObj.scale > 0) {
        activeSailsMap[sailId] = setObj.scale;
      }
    }
  });

  window.AppState.activeSails = activeSailsMap;
  if (window.renderActiveSailsDeck) {
    window.renderActiveSailsDeck();
  }
}

function updateQueryLoopDisplay(tick) {
  const cardEl = document.getElementById('zoneQueryLoop');
  const titleEl = document.getElementById('queryTitle');
  const iconEl = document.getElementById('queryPromptIcon');
  const promptEl = document.getElementById('queryPromptText');
  const statusPill = document.getElementById('queryStatusPill');
  const qState = window.QueryLoopState;

  if (!cardEl || !promptEl) return;

  const simTimeMs = tick.sim_time_ms || 0;
  const sf = tick.sensor_frame;
  const sia = tick.sia_decision;
  const gt = tick.ground_truth;
  const roll = Math.abs(sf.imu.roll_deg || 0);

  const isHazardOnset = sia.risk_score >= 0.35 || sia.hazard_id !== null || roll >= 18.0 || (gt && gt.slam_active);

  // If scrubbed back before last inquiry, reset state
  if (qState.lastTriggeredSimTimeMs !== null && simTimeMs < qState.lastTriggeredSimTimeMs - 500) {
    qState.isQueryActive = false;
    qState.isConfirmed = false;
    qState.lastTriggeredSimTimeMs = null;
    qState.lastConfirmedDecision = null;
  }

  // Detect new hazard onset -> trigger auto-pause and inquiry
  if (isHazardOnset && !qState.isConfirmed && !qState.isQueryActive) {
    qState.isQueryActive = true;
    qState.lastTriggeredSimTimeMs = simTimeMs;

    // Log diagnostic event
    if (window.Logger) {
      window.Logger.log(
        'SIA_CORE',
        'WARN',
        `Зафиксирован крен ${roll.toFixed(1)}° и риск ${sia.risk_score.toFixed(2)}. Инициирован Active Sensing запрос парусов.`,
        { roll_deg: Number(roll.toFixed(1)), risk_score: Number(sia.risk_score.toFixed(2)), hazard: sia.hazard_id || 'ROLL_SPIKE' },
        simTimeMs
      );
      window.Logger.log(
        'SIM_RUNNER',
        'INFO',
        'Симуляция автоматически поставлена на паузу для ответа шкипера.',
        null,
        simTimeMs
      );
    }

    // Auto-pause simulation so skipper can answer without rush
    if (window.AppState && window.AppState.isPlaying) {
      if (typeof window.pauseSimulation === 'function') {
        window.pauseSimulation();
      }
    }
  }

  if (qState.isConfirmed) {
    // State: Confirmed
    cardEl.className = 'zone-card zone-query-loop-card confirmed';
    if (iconEl) iconEl.textContent = '✅';
    if (statusPill) {
      statusPill.className = 'query-status-pill confirmed';
      statusPill.textContent = 'CONFIRMED';
    }
    if (titleEl) titleEl.textContent = 'CONTEXT CONFIRMED — SIA READY';
    promptEl.textContent = `SIA Core: "Конфигурация [${qState.confirmedSummary}] принята. Рекомендации пересчитаны. Нажмите ▶ Play для продолжения симуляции."`;
  } else if (qState.isQueryActive) {
    // State: Active Inquiry & Simulation Paused
    cardEl.className = 'zone-card zone-query-loop-card active-query';
    if (iconEl) iconEl.textContent = '💡';
    if (statusPill) {
      statusPill.className = 'query-status-pill paused';
      statusPill.textContent = 'PAUSED (INQUIRY)';
    }
    if (titleEl) titleEl.textContent = '💡 SIA CORE ЗАПРОС: ТЕКУЩИЕ ПАРУСА';
    promptEl.textContent = `SIA Core: "Зафиксирован крен ${roll.toFixed(1)}° и нагрузка. Капитан, укажите текущую конфигурацию парусов из гардероба и нажмите 'Подтвердить':"`;
  } else {
    // State: Standby
    cardEl.className = 'zone-card zone-query-loop-card standby';
    if (iconEl) iconEl.textContent = '🛡️';
    if (statusPill) {
      statusPill.className = 'query-status-pill';
      statusPill.textContent = 'STANDBY';
    }
    if (titleEl) titleEl.textContent = 'SKIPPER QUERY LOOP (ACTIVE SENSING)';
    promptEl.textContent = 'SIA Core: "Living sea standby. Фоновый мониторинг телеметрии активен. Запрос парусов не требуется."';
  }
}

async function submitSkipperSailConfiguration() {
  const qState = window.QueryLoopState;
  const simTimeMs = window.AppState ? (window.AppState.currentSimTimeMs || 0) : 0;
  const summaryValEl = document.getElementById('querySummaryVal');
  const summaryText = summaryValEl ? summaryValEl.textContent : 'Custom Rig';

  qState.confirmedSummary = summaryText;
  qState.isConfirmed = true;
  qState.isQueryActive = false;

  // Determine primary preset token
  let primaryPreset = 'FULL_MAIN';
  const mainSetting = qState.activeWardrobeConfig['mainsail_square_top'] || qState.activeWardrobeConfig['mainsail'];
  if (mainSetting === 'REEF_1') primaryPreset = 'REEF_1';
  else if (mainSetting === 'REEF_2') primaryPreset = 'REEF_2';
  else if (mainSetting === 'REEF_3') primaryPreset = 'REEF_3';
  else if (mainSetting === 'BARE') primaryPreset = 'BARE_POLES';

  if (qState.activeWardrobeConfig['code_zero'] === 'HOISTED') primaryPreset = 'CODE_ZERO';
  if (qState.activeWardrobeConfig['asymmetric_gennaker_a2'] === 'HOISTED' || qState.activeWardrobeConfig['parasailor'] === 'HOISTED') primaryPreset = 'GENNAKER';
  if (qState.activeWardrobeConfig['storm_jib'] === 'HOISTED') primaryPreset = 'STORM_JIB';

  try {
    const res = await fetch('/api/query-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sail_set: primaryPreset,
        active_sails: window.AppState?.activeSails || {},
        wardrobe_config: qState.activeWardrobeConfig,
        sim_time_ms: Math.round(simTimeMs),
      }),
    });
    const result = await res.json();

    if (result.status === 'recalculated') {
      qState.lastConfirmedDecision = result.selected_response;
      qState.lastConfirmedCandidates = result.candidates;
      qState.lastConfirmedNote = result.note;

      // Mutate remaining simulation ticks from simTimeMs onward so timeline preserves recalculated advice
      if (window.AppState && window.AppState.data && Array.isArray(window.AppState.data.ticks)) {
        const curMs = Math.round(simTimeMs);
        window.AppState.data.ticks.forEach(t => {
          if (t.sim_time_ms >= curMs) {
            t.sia_decision.selected_response = result.selected_response;
            t.sia_decision.candidates = result.candidates;
            t.sia_decision.note = result.note;
            if (result.selected_response) {
              t.sia_decision.risk_score = Math.min(t.sia_decision.risk_score, 0.40);
            }
          }
        });
      }

      // Update Zone 4 Candidate Responses in DOM
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

      // Update primary card in DOM
      const sel = result.selected_response;
      if (sel) {
        const scoreEl = document.getElementById('primaryScore');
        const titleEl = document.getElementById('primaryActionTitle');
        const rudEl = document.getElementById('cmdRudder');
        const sailEl = document.getElementById('cmdSail');
        if (scoreEl) scoreEl.textContent = `SCORE: ${sel.priority_score.toFixed(2)}`;
        if (titleEl) titleEl.textContent = sel.action_type.replace(/_/g, ' ');
        if (rudEl) rudEl.textContent = sel.rudder_command_deg !== null ? `${sel.rudder_command_deg.toFixed(1)}°` : 'NONE';
        if (sailEl) sailEl.textContent = sel.sail_command_pct !== null ? `${sel.sail_command_pct.toFixed(0)}%` : 'MAINTAIN';
      }

      // Update reasoning note in DOM
      const noteEl = document.getElementById('siaReasoningNote');
      if (noteEl) {
        noteEl.textContent = result.note;
      }

      // Record logs into Service Logger
      if (window.Logger) {
        window.Logger.log(
          'SKIPPER',
          'ACTION',
          `Капитан подтвердил паруса: [${summaryText}]`,
          { preset: primaryPreset, wardrobe: qState.activeWardrobeConfig },
          simTimeMs
        );
        if (sel) {
          window.Logger.log(
            'SIA_CORE',
            'INFO',
            `СИА пересчитала решение: ${sel.action_type.replace(/_/g, ' ')} (Score: ${sel.priority_score.toFixed(2)})`,
            { rule_ids: sel.rule_ids, note: result.note, candidates_count: result.candidates?.length },
            simTimeMs
          );
        }
        window.Logger.log(
          'PHYSICS',
          'INFO',
          `Аэродинамическая модель парусов обновлена под пресет ${primaryPreset}`,
          null,
          simTimeMs
        );
      }
    }
  } catch (err) {
    console.error('Failed to dispatch skipper wardrobe action:', err);
    if (window.Logger) {
      window.Logger.log('SIA_CORE', 'CRIT', `Ошибка отправки конфигурации: ${err.message}`, null, simTimeMs);
    }
  }

  renderQueryWardrobe();
}

window.renderQueryWardrobe = renderQueryWardrobe;
window.renderQueryActions = renderQueryWardrobe; // Backwards compatibility alias
window.updateQueryLoopDisplay = updateQueryLoopDisplay;

