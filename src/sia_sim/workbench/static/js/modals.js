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
          window.TimelineRenderer ? window.TimelineRenderer.events : null
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
      if (window.AppState.customVessel) {
        const ht = document.getElementById('customHullType');
        if (ht) ht.value = window.AppState.customVessel.hull_type || 'monohull';
        const loa = document.getElementById('customLoa');
        if (loa) loa.value = window.AppState.customVessel.loa_m || 13.94;
        const beam = document.getElementById('customBeam');
        if (beam) beam.value = window.AppState.customVessel.beam_m || 4.50;
        const mass = document.getElementById('customDisplacement');
        if (mass) mass.value = window.AppState.customVessel.displacement_kg || 10550;
        const mast = document.getElementById('customMastHeight');
        if (mast) mast.value = window.AppState.customVessel.mast_height_m || 19.5;
        const area = document.getElementById('customSailArea');
        if (area) area.value = window.AppState.customVessel.sail_area_m2 || 100.0;
        const avail = window.AppState.customVessel.available_sails || allSailIds;
        allSailIds.forEach((id) => {
          const cb = document.getElementById(`inv_${id}`);
          if (cb) cb.checked = avail.includes(id);
        });
      }
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

      closeCustomVesselModal();
      if (window.loadScenario) {
        window.loadScenario(
          window.AppState.scenarioId,
          window.AppState.seed,
          window.AppState.durationS,
          window.TimelineRenderer ? window.TimelineRenderer.events : null
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
  bindModalControls,
  openEventInspector,
};
