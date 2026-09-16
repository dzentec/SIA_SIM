/**
 * SIA Simulation Workbench — State Management Module
 */

const AppState = {
  scenarioId: 'coastal_cruise',
  vesselPreset: 'beneteau_oceanis_45',
  sailPlan: 'FULL_MAIN',
  activeSails: { mainsail: 1.0, genoa: 1.0 },
  seed: 42,
  durationS: 600,
  imuRate: 10,
  damping: 'normal',
  customWorld: null,
  customVessel: null,
  data: null,
  currentSimTimeMs: 0.0,
  isPlaying: false,
  isLivingSeaRunning: false,
  speedMultiplier: 2.0,
  rafId: null,
  lastWallTimestamp: null,
  mode: 'live', // 'live' | 'debug'
  selectedEvent: null,
};

window.AppState = AppState;
