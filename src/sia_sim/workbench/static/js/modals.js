/**
 * SIA Simulation Workbench — Modals Controller Module
 * Handles Custom World Preset, Custom Vessel & Sail Inventory, and Event Inspector Modals.
 */

const allSailIds = [
  'mainsail_square_top',
  'solent_jib',
  'genoa_furling',
  'code_zero',
  'asymmetric_gennaker_a2',
  'asymmetric_gennaker_a3',
  'parasailor',
  'storm_jib'
];

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

      window.AppState.customWorld = {
        initial_tws_kt: tws,
        initial_twa_deg: twa,
        initial_wave_height_m: waveH,
        initial_wave_period_s: waveT,
        initial_sog_kt: sog,
        initial_heading_deg: heading,
        initial_heel_deg: heel,
      };

      closeCustomModal();
      if (window.loadScenario) {
        window.loadScenario(
          window.AppState.scenarioId,
          window.AppState.seed,
          window.AppState.durationS,
          window.TimelineRenderer ? window.TimelineRenderer.events : null,
          true
        );
      }
    });
  }
}

const sailLabels = {
  mainsail_square_top: 'Mainsail (Square-Top)',
  genoa_furling: 'Genoa (Furling 130%)',
  solent_jib: 'Solent Jib (100%)',
  storm_jib: 'Storm Jib (Heavy Weather)',
  code_zero: 'Code 0 (Reaching)',
  asymmetric_gennaker_a2: 'Gennaker A2 (Downwind)',
  asymmetric_gennaker_a3: 'Gennaker A3 (Medium)',
  parasailor: 'Parasailor (Spinnaker)'
};

function getAvailableSailsForCurrentVessel() {
  if (window.AppState && window.AppState.customVessel && Array.isArray(window.AppState.customVessel.available_sails)) {
    return window.AppState.customVessel.available_sails;
  }
  const isIOR = window.AppState && window.AppState.vesselPreset === 'monohull_ior';
  return isIOR
    ? ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'storm_jib']
    : ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'code_zero', 'asymmetric_gennaker_a2', 'storm_jib'];
}

function populateActiveSailPlanModal() {
  const availableSails = getAvailableSailsForCurrentVessel();
  const currentSlots = (window.AppState && window.AppState.tackSlots) || {
    main: 'mainsail_square_top',
    inner: null,
    outer: 'genoa_furling',
    bowsprit: null,
  };

  // 1. Main Slot
  const selMain = document.getElementById('selSlotMain');
  if (selMain) {
    let html = '<option value="">-- Doused / Bare --</option>';
    ['mainsail_square_top'].forEach((id) => {
      if (availableSails.includes(id)) {
        html += `<option value="${id}">${sailLabels[id] || id}</option>`;
      }
    });
    selMain.innerHTML = html;
    selMain.value = currentSlots.main || '';
  }

  // 2. Inner Stay Slot
  const selInner = document.getElementById('selSlotInner');
  if (selInner) {
    let html = '<option value="">-- None / Furled --</option>';
    ['solent_jib', 'storm_jib'].forEach((id) => {
      if (availableSails.includes(id)) {
        html += `<option value="${id}">${sailLabels[id] || id}</option>`;
      }
    });
    selInner.innerHTML = html;
    selInner.value = currentSlots.inner || '';
  }

  // 3. Outer Forestay Slot
  const selOuter = document.getElementById('selSlotOuter');
  if (selOuter) {
    let html = '<option value="">-- None / Furled --</option>';
    ['genoa_furling', 'solent_jib'].forEach((id) => {
      if (availableSails.includes(id)) {
        html += `<option value="${id}">${sailLabels[id] || id}</option>`;
      }
    });
    selOuter.innerHTML = html;
    selOuter.value = currentSlots.outer || '';
  }

  // 4. Bowsprit Slot
  const selBow = document.getElementById('selSlotBowsprit');
  if (selBow) {
    let html = '<option value="">-- None / Packed --</option>';
    ['code_zero', 'asymmetric_gennaker_a2', 'asymmetric_gennaker_a3', 'parasailor'].forEach((id) => {
      if (availableSails.includes(id)) {
        html += `<option value="${id}">${sailLabels[id] || id}</option>`;
      }
    });
    selBow.innerHTML = html;
    selBow.value = currentSlots.bowsprit || '';
  }
}

function bindActiveSailPlanModalControls() {
  const backdrop = document.getElementById('activeSailPlanModalBackdrop');
  const btnClose = document.getElementById('btnActiveSailPlanClose');
  const btnCancel = document.getElementById('btnActiveSailPlanCancel');
  const btnApply = document.getElementById('btnActiveSailPlanApply');

  const closeModal = () => {
    if (backdrop) backdrop.style.display = 'none';
  };

  if (btnClose) btnClose.addEventListener('click', closeModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);

  // Quick preset macro buttons inside modal
  const quickBtns = document.querySelectorAll('#sailPlanQuickPresets .btn-sail-quick');
  quickBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const plan = btn.getAttribute('data-plan');
      const available = getAvailableSailsForCurrentVessel();
      const selMain = document.getElementById('selSlotMain');
      const selInner = document.getElementById('selSlotInner');
      const selOuter = document.getElementById('selSlotOuter');
      const selBow = document.getElementById('selSlotBowsprit');

      if (plan === 'CRUISE') {
        if (selMain) selMain.value = available.includes('mainsail_square_top') ? 'mainsail_square_top' : '';
        if (selInner) selInner.value = '';
        if (selOuter) selOuter.value = available.includes('genoa_furling') ? 'genoa_furling' : (available.includes('solent_jib') ? 'solent_jib' : '');
        if (selBow) selBow.value = '';
      } else if (plan === 'RACE_CODE0') {
        if (selMain) selMain.value = available.includes('mainsail_square_top') ? 'mainsail_square_top' : '';
        if (selInner) selInner.value = '';
        if (selOuter) selOuter.value = '';
        if (selBow) selBow.value = available.includes('code_zero') ? 'code_zero' : '';
      } else if (plan === 'DOWNWIND') {
        if (selMain) selMain.value = available.includes('mainsail_square_top') ? 'mainsail_square_top' : '';
        if (selInner) selInner.value = '';
        if (selOuter) selOuter.value = '';
        if (selBow) selBow.value = available.includes('asymmetric_gennaker_a2') ? 'asymmetric_gennaker_a2' : (available.includes('parasailor') ? 'parasailor' : (available.includes('code_zero') ? 'code_zero' : ''));
      } else if (plan === 'STORM') {
        if (selMain) selMain.value = '';
        if (selInner) selInner.value = available.includes('storm_jib') ? 'storm_jib' : (available.includes('solent_jib') ? 'solent_jib' : '');
        if (selOuter) selOuter.value = '';
        if (selBow) selBow.value = '';
      } else if (plan === 'BARE_POLES') {
        if (selMain) selMain.value = '';
        if (selInner) selInner.value = '';
        if (selOuter) selOuter.value = '';
        if (selBow) selBow.value = '';
      }
    });
  });

  if (btnApply) {
    btnApply.addEventListener('click', () => {
      const selMain = document.getElementById('selSlotMain');
      const selInner = document.getElementById('selSlotInner');
      const selOuter = document.getElementById('selSlotOuter');
      const selBow = document.getElementById('selSlotBowsprit');

      const newTackSlots = {
        main: (selMain && selMain.value) || null,
        inner: (selInner && selInner.value) || null,
        outer: (selOuter && selOuter.value) || null,
        bowsprit: (selBow && selBow.value) || null,
      };

      window.AppState.tackSlots = newTackSlots;

      // Map to activeSails dictionary for physics engine
      const newActiveSails = {};
      if (newTackSlots.main) newActiveSails.mainsail = 1.0;
      if (newTackSlots.outer === 'genoa_furling') newActiveSails.genoa = 1.0;
      else if (newTackSlots.outer === 'solent_jib') newActiveSails.solent_jib = 1.0;

      if (newTackSlots.inner === 'solent_jib') newActiveSails.solent_jib = 1.0;
      else if (newTackSlots.inner === 'storm_jib') newActiveSails.storm_jib = 1.0;

      if (newTackSlots.bowsprit === 'code_zero') newActiveSails.code_zero = 1.0;
      else if (
        newTackSlots.bowsprit === 'asymmetric_gennaker_a2' ||
        newTackSlots.bowsprit === 'asymmetric_gennaker_a3' ||
        newTackSlots.bowsprit === 'parasailor'
      ) {
        newActiveSails.gennaker = 1.0;
      }

      window.AppState.activeSails = newActiveSails;

      // Broadcast across sync channel
      if (window.CockpitController && window.CockpitController.syncChannel) {
        window.CockpitController.syncChannel.postMessage({
          type: 'SAIL_PLAN_SYNC',
          tackSlots: newTackSlots,
          activeSails: newActiveSails,
          vesselPreset: window.AppState.vesselPreset,
          customVessel: window.AppState.customVessel,
        });
      }

      // Update cockpit visuals
      if (window.CockpitController && window.CockpitController.updateActiveSailPlanVisuals) {
        window.CockpitController.updateActiveSailPlanVisuals();
      }

      // Update wardrobe tags in workbench
      if (window.renderVesselWardrobe) {
        window.renderVesselWardrobe();
      }

      closeModal();

      if (window.loadScenario) {
        window.loadScenario(
          window.AppState.scenarioId,
          window.AppState.seed,
          window.AppState.durationS,
          window.TimelineRenderer ? window.TimelineRenderer.events : null,
          true
        );
      }
    });
  }
}

function bindCustomVesselControls() {
  const btnCustom = document.getElementById('btnCustomVessel');
  const backdrop = document.getElementById('customVesselModalBackdrop');
  const btnClose = document.getElementById('btnCustomVesselClose');
  const btnCancel = document.getElementById('btnCustomVesselCancel');
  const btnApply = document.getElementById('btnCustomVesselApply');

  const vspecLoa = document.getElementById('vspecLoa');
  const vspecBeam = document.getElementById('vspecBeam');
  const vspecMass = document.getElementById('vspecMass');
  const vspecArea = document.getElementById('vspecArea');

  if (btnCustom && backdrop) {
    btnCustom.addEventListener('click', () => {
      const isIOR = window.AppState.vesselPreset === 'monohull_ior';
      const defaultLoa = isIOR ? 10.50 : 13.94;
      const defaultBeam = isIOR ? 3.20 : 4.50;
      const defaultMass = isIOR ? 4500 : 10550;
      const defaultMast = isIOR ? 14.0 : 19.5;
      const defaultArea = isIOR ? 45.0 : 100.0;
      const defaultSails = isIOR
        ? ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'storm_jib']
        : ['mainsail_square_top', 'solent_jib', 'genoa_furling', 'code_zero', 'asymmetric_gennaker_a2', 'storm_jib'];

      const cv = window.AppState.customVessel;
      const ht = document.getElementById('customHullType');
      if (ht) ht.value = cv?.hull_type || 'monohull';
      const loa = document.getElementById('customLoa');
      if (loa) loa.value = cv?.loa_m || defaultLoa;
      const beam = document.getElementById('customBeam');
      if (beam) beam.value = cv?.beam_m || defaultBeam;
      const mass = document.getElementById('customDisplacement');
      if (mass) mass.value = cv?.displacement_kg || defaultMass;
      const mast = document.getElementById('customMastHeight');
      if (mast) mast.value = cv?.mast_height_m || defaultMast;
      const area = document.getElementById('customSailArea');
      if (area) area.value = cv?.sail_area_m2 || defaultArea;

      const avail = cv?.available_sails || defaultSails;
      allSailIds.forEach((id) => {
        const cb = document.getElementById(`inv_${id}`);
        if (cb) cb.checked = avail.includes(id);
      });

      backdrop.style.display = 'flex';
    });
  }

  const closeCustomVesselModal = () => {
    if (backdrop) backdrop.style.display = 'none';
  };

  if (btnClose) btnClose.addEventListener('click', closeCustomVesselModal);
  if (btnCancel) btnCancel.addEventListener('click', closeCustomVesselModal);

  if (btnApply) {
    btnApply.addEventListener('click', () => {
      const hullType = document.getElementById('customHullType') ? document.getElementById('customHullType').value : 'monohull';
      const loa = parseFloat(document.getElementById('customLoa').value) || 13.94;
      const beam = parseFloat(document.getElementById('customBeam').value) || 4.50;
      const mass = parseFloat(document.getElementById('customDisplacement').value) || 10550;
      const mast = parseFloat(document.getElementById('customMastHeight').value) || 19.5;
      const sailArea = parseFloat(document.getElementById('customSailArea').value) || 100.0;

      const checkedSails = allSailIds.filter((id) => {
        const el = document.getElementById(`inv_${id}`);
        return el && el.checked;
      });

      if (checkedSails.length === 0) {
        alert('Please select at least one available sail for your inventory.');
        return;
      }

      window.AppState.customVessel = {
        hull_type: hullType,
        loa_m: loa,
        beam_m: beam,
        displacement_kg: mass,
        mast_height_m: mast,
        sail_area_m2: sailArea,
        available_sails: checkedSails,
      };

      if (vspecLoa) vspecLoa.textContent = `${loa.toFixed(2)} m`;
      if (vspecBeam) vspecBeam.textContent = `${beam.toFixed(2)} m`;
      if (vspecMass) vspecMass.textContent = `${mass.toLocaleString()} kg`;
      if (vspecArea) vspecArea.textContent = `${sailArea.toFixed(0)} m²`;

      // Filter active tack slots if any decommissioned from wardrobe
      const currentSlots = window.AppState.tackSlots || {};
      const newTackSlots = {
        main: checkedSails.includes(currentSlots.main) ? currentSlots.main : (checkedSails.includes('mainsail_square_top') ? 'mainsail_square_top' : null),
        inner: checkedSails.includes(currentSlots.inner) ? currentSlots.inner : null,
        outer: checkedSails.includes(currentSlots.outer) ? currentSlots.outer : (checkedSails.includes('genoa_furling') ? 'genoa_furling' : null),
        bowsprit: checkedSails.includes(currentSlots.bowsprit) ? currentSlots.bowsprit : null,
      };
      window.AppState.tackSlots = newTackSlots;

      const newActiveSails = {};
      if (newTackSlots.main) newActiveSails.mainsail = 1.0;
      if (newTackSlots.outer === 'genoa_furling') newActiveSails.genoa = 1.0;
      else if (newTackSlots.outer === 'solent_jib') newActiveSails.solent_jib = 1.0;
      if (newTackSlots.inner === 'solent_jib') newActiveSails.solent_jib = 1.0;
      else if (newTackSlots.inner === 'storm_jib') newActiveSails.storm_jib = 1.0;
      if (newTackSlots.bowsprit === 'code_zero') newActiveSails.code_zero = 1.0;
      else if (['asymmetric_gennaker_a2', 'asymmetric_gennaker_a3', 'parasailor'].includes(newTackSlots.bowsprit)) {
        newActiveSails.gennaker = 1.0;
      }
      window.AppState.activeSails = newActiveSails;

      if (window.renderVesselWardrobe) {
        window.renderVesselWardrobe();
      }
      if (window.CockpitController && window.CockpitController.updateActiveSailPlanVisuals) {
        window.CockpitController.updateActiveSailPlanVisuals();
      }
      populateActiveSailPlanModal();

      closeCustomVesselModal();
      if (window.loadScenario) {
        window.loadScenario(
          window.AppState.scenarioId,
          window.AppState.seed,
          window.AppState.durationS,
          window.TimelineRenderer ? window.TimelineRenderer.events : null,
          true
        );
      }
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
      window.AppState.selectedEvent = null;
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
      if (window.AppState.selectedEvent && window.TimelineRenderer) {
        window.TimelineRenderer.deleteEvent(window.AppState.selectedEvent.event_id);
      }
      if (backdrop) backdrop.style.display = 'none';
      window.AppState.selectedEvent = null;
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', () => {
      if (!window.AppState.selectedEvent) return;
      const timeSec = parseFloat(document.getElementById('modalEventTime').value) || 0.0;
      const durSec = parseFloat(document.getElementById('modalEventDuration').value) || 2.0;
      const timeMs = Math.round(timeSec * 1000);
      const durMs = Math.round(durSec * 1000);
      const type = document.getElementById('modalEventType').value;
      const paramVal = parseFloat(document.getElementById('modalEventParam').value) || 10.0;

      window.AppState.selectedEvent.sim_time_ms = timeMs;
      window.AppState.selectedEvent.event_type = type;

      if (type === 'wind_gust') {
        window.AppState.selectedEvent.parameters = {
          tws_kt: paramVal,
          duration_ms: durMs,
          duration_s: durSec,
          direction_shift_deg: 15.0,
        };
      } else if (type === 'wave_impact') {
        window.AppState.selectedEvent.parameters = {
          impact_force_n: paramVal * 1000.0,
          impact_roll_moment_nm: -paramVal * 2000.0,
          duration_ms: durMs,
          duration_s: durSec,
        };
      } else {
        window.AppState.selectedEvent.parameters = {
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
      window.AppState.selectedEvent = null;
    });
  }
}

function openEventInspector(evt) {
  window.AppState.selectedEvent = evt;
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
window.ModalsController = {
  bindCustomWorldControls,
  bindCustomVesselControls,
  bindActiveSailPlanModalControls,
  populateActiveSailPlanModal,
  getAvailableSailsForCurrentVessel,
  bindModalControls,
  openEventInspector,
};

