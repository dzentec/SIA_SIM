/**
 * High-Performance Marine Canvas Dial Instruments (60 FPS)
 * Strict conformance with authentic Raymarine / B&G Marine Instruments
 */

const InstrumentRenderer = {

  // Physical Needle Damping & Inertia Engine (Raymarine / B&G standard)
  dampingMode: 'normal', // 'none' | 'normal' (tau=0.35s) | 'heavy' (tau=0.75s)
  _smoothed: {
    awa: null,
    aws: null,
    heel: null,
    cog: null,
    sog: null,
    pitch: null,
    heave: null,
    accelZ: null,
    slam: null,
    lastTime: performance.now(),
  },

  setDampingMode(mode) {
    if (['none', 'normal', 'heavy'].includes(mode)) {
      this.dampingMode = mode;
    }
  },

  _getTau() {
    if (this.dampingMode === 'none') return 0.001;
    if (this.dampingMode === 'heavy') return 0.75;
    return 0.35; // Standard marine instrument damping ~350ms
  },

  _smoothLinear(key, target, dtSec) {
    if (target === null || target === undefined || isNaN(target)) return target;
    const cur = this._smoothed[key];
    if (cur === null || cur === undefined || this.dampingMode === 'none') {
      this._smoothed[key] = target;
      return target;
    }
    const tau = this._getTau();
    const alpha = 1.0 - Math.exp(-dtSec / tau);
    const updated = cur + alpha * (target - cur);
    this._smoothed[key] = updated;
    return updated;
  },

  _smoothAngle(key, targetDeg, dtSec) {
    if (targetDeg === null || targetDeg === undefined || isNaN(targetDeg)) return targetDeg;
    const cur = this._smoothed[key];
    if (cur === null || cur === undefined || this.dampingMode === 'none') {
      this._smoothed[key] = targetDeg;
      return targetDeg;
    }
    const tau = this._getTau();
    const alpha = 1.0 - Math.exp(-dtSec / tau);
    let diff = targetDeg - cur;
    while (diff > 180) diff -= 360;
    while (diff < -180) diff += 360;
    const updated = cur + alpha * diff;
    this._smoothed[key] = updated;
    return updated;
  },

  /**
   * Renders the Apparent Wind (AWA / AWS) Marine Gauge
   * @param {HTMLCanvasElement} canvas
   * @param {number|null} awa Apparent Wind Angle (-180 to +180)
   * @param {number|null} aws Apparent Wind Speed in knots
   * @param {boolean} fault Sensor fault state
   */
  drawWindDial(canvas, rawAwa, rawAws, fault = false) {
    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    this._smoothed.lastTime = now;

    const awa = this._smoothAngle('awa', rawAwa, dt);
    const aws = this._smoothLinear('aws', rawAws, dt);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);

    // Bezel & Background
    ctx.beginPath();
    ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
    ctx.fillStyle = '#0a101d';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#1f2d47';
    ctx.stroke();

    // Colored Sectors: Port (Red, Left) & Starboard (Green, Right)
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2, true);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.4)';
    ctx.lineWidth = 6;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2, false);
    ctx.strokeStyle = 'rgba(0, 230, 118, 0.4)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Dial Ticks & Degree Labels
    for (let deg = 0; deg < 360; deg += 30) {
      const rad = ((deg - 90) * Math.PI) / 180;
      const isMajor = deg % 60 === 0;
      const innerR = isMajor ? r - 12 : r - 6;

      const x1 = cx + Math.cos(rad) * r;
      const y1 = cy + Math.sin(rad) * r;
      const x2 = cx + Math.cos(rad) * innerR;
      const y2 = cy + Math.sin(rad) * innerR;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = isMajor ? '#94a3b8' : '#475569';
      ctx.lineWidth = isMajor ? 2 : 1;
      ctx.stroke();

      if (isMajor) {
        const textR = r - 22;
        const tx = cx + Math.cos(rad) * textR;
        const ty = cy + Math.sin(rad) * textR;
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        let label = deg;
        if (deg > 180) label = 360 - deg;
        ctx.fillText(label.toString(), tx, ty);
      }
    }

    // Needle Pointer with Damped Movement
    if (!fault && awa !== null) {
      const angleRad = ((awa - 90) * Math.PI) / 180;
      
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angleRad + Math.PI / 2);

      // Pointer Arrow
      ctx.beginPath();
      ctx.moveTo(0, -r + 14);
      ctx.lineTo(-8, -r + 32);
      ctx.lineTo(8, -r + 32);
      ctx.closePath();
      ctx.fillStyle = awa < 0 ? '#ff1744' : '#00e676';
      ctx.fill();

      // Needle Line
      ctx.beginPath();
      ctx.moveTo(0, -r + 30);
      ctx.lineTo(0, 20);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.restore();
    }

    // Center Hub & Speed Readout
    ctx.beginPath();
    ctx.arc(cx, cy, 32, 0, Math.PI * 2);
    ctx.fillStyle = '#111827';
    ctx.fill();
    ctx.strokeStyle = '#1f2d47';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (fault || aws === null) {
      ctx.fillStyle = '#ffb300';
      ctx.font = 'bold 14px "JetBrains Mono", monospace';
      ctx.fillText('---', cx, cy - 2);
      ctx.font = '8px "Inter", sans-serif';
      ctx.fillText('NO SIGNAL', cx, cy + 12);
    } else {
      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 15px "JetBrains Mono", monospace';
      ctx.fillText(aws.toFixed(1), cx, cy - 4);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '9px "Inter", sans-serif';
      ctx.fillText('KTS', cx, cy + 12);
    }
  },

  /**
   * Renders the Heel Inclinometer Instrument
   * @param {HTMLCanvasElement} canvas
   * @param {number|null} heel Heel angle in degrees (negative = port)
   * @param {boolean} fault Sensor fault state
   */
  drawHeelDial(canvas, rawHeel, fault = false) {
    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    const heel = this._smoothLinear('heel', rawHeel, dt);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);

    // Bezel
    ctx.beginPath();
    ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
    ctx.fillStyle = '#0a101d';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#1f2d47';
    ctx.stroke();

    // Scale Arc (±45 degrees)
    const startArc = ((90 - 45) * Math.PI) / 180;
    const endArc = ((90 + 45) * Math.PI) / 180;

    // Normal safe zone (0 to 18 deg)
    ctx.beginPath();
    ctx.arc(cx, cy, r, ((90 - 18) * Math.PI) / 180, ((90 + 18) * Math.PI) / 180);
    ctx.strokeStyle = 'rgba(0, 230, 118, 0.4)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Warning zones (18 to 25 deg)
    ctx.beginPath();
    ctx.arc(cx, cy, r, ((90 - 25) * Math.PI) / 180, ((90 - 18) * Math.PI) / 180);
    ctx.strokeStyle = 'rgba(255, 179, 0, 0.6)';
    ctx.lineWidth = 6;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, r, ((90 + 18) * Math.PI) / 180, ((90 + 25) * Math.PI) / 180);
    ctx.strokeStyle = 'rgba(255, 179, 0, 0.6)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Danger zones (>25 deg)
    ctx.beginPath();
    ctx.arc(cx, cy, r, ((90 - 45) * Math.PI) / 180, ((90 - 25) * Math.PI) / 180);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.7)';
    ctx.lineWidth = 6;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, r, ((90 + 25) * Math.PI) / 180, ((90 + 45) * Math.PI) / 180);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.7)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Ticks on lower arc
    for (let deg = -40; deg <= 40; deg += 10) {
      const rad = ((90 + deg) * Math.PI) / 180;
      const isMajor = deg % 20 === 0;
      const innerR = isMajor ? r - 10 : r - 5;

      const x1 = cx + Math.cos(rad) * r;
      const y1 = cy + Math.sin(rad) * r;
      const x2 = cx + Math.cos(rad) * innerR;
      const y2 = cy + Math.sin(rad) * innerR;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = isMajor ? '#94a3b8' : '#475569';
      ctx.lineWidth = isMajor ? 2 : 1;
      ctx.stroke();

      if (isMajor) {
        const textR = r - 18;
        const tx = cx + Math.cos(rad) * textR;
        const ty = cy + Math.sin(rad) * textR;
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.abs(deg).toString(), tx, ty);
      }
    }

    // Yacht Hull Silhouette (Rotates with Heel)
    const effectiveHeel = (fault || heel === null) ? 0 : heel;
    const heelRad = (effectiveHeel * Math.PI) / 180;

    ctx.save();
    ctx.translate(cx, cy - 8);
    ctx.rotate(heelRad);

    // Mast
    ctx.beginPath();
    ctx.moveTo(0, -36);
    ctx.lineTo(0, 10);
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Hull Cross Section
    ctx.beginPath();
    ctx.moveTo(-28, 0);
    ctx.lineTo(28, 0);
    ctx.lineTo(20, 16);
    ctx.lineTo(0, 24);
    ctx.lineTo(-20, 16);
    ctx.closePath();
    ctx.fillStyle = '#1e293b';
    ctx.fill();
    ctx.strokeStyle = Math.abs(effectiveHeel) >= 25 ? '#ff1744' : (Math.abs(effectiveHeel) >= 18 ? '#ffb300' : '#00e5ff');
    ctx.lineWidth = 2;
    ctx.stroke();

    // Keel bulb
    ctx.beginPath();
    ctx.moveTo(0, 24);
    ctx.lineTo(0, 36);
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.restore();

    // Digital Readout
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (fault || heel === null) {
      ctx.fillStyle = '#ffb300';
      ctx.font = 'bold 14px "JetBrains Mono", monospace';
      ctx.fillText('---', cx, cy + 34);
    } else {
      ctx.fillStyle = Math.abs(heel) >= 25 ? '#ff1744' : (Math.abs(heel) >= 18 ? '#ffb300' : '#00e5ff');
      ctx.font = 'bold 15px "JetBrains Mono", monospace';
      const side = heel < 0 ? 'P ' : (heel > 0 ? 'S ' : '');
      ctx.fillText(`${side}${Math.abs(heel).toFixed(1)}°`, cx, cy + 34);
    }
  },

  /**
   * Renders the Navigation (SOG / COG) Compass Rose
   * @param {HTMLCanvasElement} canvas
   * @param {number|null} cog Course Over Ground in degrees
   * @param {number|null} sog Speed Over Ground in knots
   * @param {boolean} fault GPS fault / no-fix
   */
  drawNavDial(canvas, rawCog, rawSog, fault = false) {
    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    const cog = this._smoothAngle('cog', rawCog, dt);
    const sog = this._smoothLinear('sog', rawSog, dt);
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);

    // Bezel
    ctx.beginPath();
    ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
    ctx.fillStyle = '#0a101d';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#1f2d47';
    ctx.stroke();

    // Compass ticks
    for (let deg = 0; deg < 360; deg += 15) {
      const rad = ((deg - 90) * Math.PI) / 180;
      const isCardinal = deg % 90 === 0;
      const isMajor = deg % 45 === 0;
      const innerR = isCardinal ? r - 12 : (isMajor ? r - 8 : r - 5);

      const x1 = cx + Math.cos(rad) * r;
      const y1 = cy + Math.sin(rad) * r;
      const x2 = cx + Math.cos(rad) * innerR;
      const y2 = cy + Math.sin(rad) * innerR;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = isCardinal ? '#00e5ff' : (isMajor ? '#94a3b8' : '#475569');
      ctx.lineWidth = isCardinal ? 2 : 1;
      ctx.stroke();

      if (isCardinal) {
        const textR = r - 20;
        const tx = cx + Math.cos(rad) * textR;
        const ty = cy + Math.sin(rad) * textR;
        ctx.fillStyle = deg === 0 ? '#ff1744' : '#00e5ff';
        ctx.font = 'bold 11px "Inter", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const cardLabels = { 0: 'N', 90: 'E', 180: 'S', 270: 'W' };
        ctx.fillText(cardLabels[deg], tx, ty);
      }
    }

    // Heading / Course Needle
    if (!fault && cog !== null) {
      const cogRad = ((cog - 90) * Math.PI) / 180;
      
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(cogRad + Math.PI / 2);

      // Arrow
      ctx.beginPath();
      ctx.moveTo(0, -r + 14);
      ctx.lineTo(-6, -r + 28);
      ctx.lineTo(6, -r + 28);
      ctx.closePath();
      ctx.fillStyle = '#00e5ff';
      ctx.fill();

      // Line
      ctx.beginPath();
      ctx.moveTo(0, -r + 28);
      ctx.lineTo(0, 16);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.restore();
    }

    // Center SOG Readout
    ctx.beginPath();
    ctx.arc(cx, cy, 30, 0, Math.PI * 2);
    ctx.fillStyle = '#111827';
    ctx.fill();
    ctx.strokeStyle = '#1f2d47';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (fault || sog === null) {
      ctx.fillStyle = '#ffb300';
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.fillText('NO FIX', cx, cy - 2);
    } else {
      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 15px "JetBrains Mono", monospace';
      ctx.fillText(sog.toFixed(1), cx, cy - 4);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '9px "Inter", sans-serif';
      ctx.fillText('SOG KT', cx, cy + 12);
    }
  },

  /**
   * Renders the Pitch / Trim Inclinometer (Килевая качка)
   * @param {HTMLCanvasElement} canvas
   * @param {number|null} pitchDeg Pitch angle in degrees (+ bow up, - bow down)
   * @param {number|null} pitchRateDegS Pitch angular rate in deg/s
   * @param {boolean} fault Sensor fault state
   */
  drawPitchDial(canvas, rawPitchDeg, pitchRateDegS, fault = false) {
    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    const pitchDeg = this._smoothLinear('pitch', rawPitchDeg, dt);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);

    // Bezel
    ctx.beginPath();
    ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
    ctx.fillStyle = '#0a101d';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#1f2d47';
    ctx.stroke();

    // Scale Arc (±20 degrees) on right side
    const safeArcTop = ((0 - 6) * Math.PI) / 180;
    const safeArcBottom = ((0 + 6) * Math.PI) / 180;

    // Safe zone (-6 to +6 deg)
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 6, Math.PI / 6);
    ctx.strokeStyle = 'rgba(0, 230, 118, 0.4)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Warning zones (±6 to ±12 deg)
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 3, -Math.PI / 6);
    ctx.strokeStyle = 'rgba(255, 179, 0, 0.6)';
    ctx.lineWidth = 6;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI / 6, Math.PI / 3);
    ctx.strokeStyle = 'rgba(255, 179, 0, 0.6)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Danger zones (> ±12 deg)
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 3);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.7)';
    ctx.lineWidth = 6;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI / 3, Math.PI / 2);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.7)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Ticks
    for (let deg = -20; deg <= 20; deg += 5) {
      const rad = (deg * Math.PI) / 180;
      const isMajor = deg % 10 === 0;
      const innerR = isMajor ? r - 10 : r - 5;

      const x1 = cx + Math.cos(rad) * r;
      const y1 = cy + Math.sin(rad) * r;
      const x2 = cx + Math.cos(rad) * innerR;
      const y2 = cy + Math.sin(rad) * innerR;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = isMajor ? '#94a3b8' : '#475569';
      ctx.lineWidth = isMajor ? 2 : 1;
      ctx.stroke();

      if (isMajor) {
        const textR = r - 18;
        const tx = cx + Math.cos(rad) * textR;
        const ty = cy + Math.sin(rad) * textR;
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(deg.toString(), tx, ty);
      }
    }

    // Side Profile Yacht Silhouette (Tilts with Pitch)
    const effectivePitch = (fault || pitchDeg === null) ? 0 : pitchDeg;
    // Rotate: positive pitch (bow up) tilts right side up / left side down
    const pitchRad = (-effectivePitch * Math.PI) / 180;

    ctx.save();
    ctx.translate(cx, cy - 6);
    ctx.rotate(pitchRad);

    // Mast
    ctx.beginPath();
    ctx.moveTo(-4, -34);
    ctx.lineTo(-4, 6);
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Boom & Sail hint
    ctx.beginPath();
    ctx.moveTo(-4, -8);
    ctx.lineTo(-24, -2);
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Side Profile Hull
    ctx.beginPath();
    ctx.moveTo(-32, 2);   // Transom stern
    ctx.lineTo(28, 0);    // Bow top
    ctx.lineTo(34, 6);    // Bow stem
    ctx.lineTo(16, 16);   // Forefoot
    ctx.lineTo(-12, 16);  // Keel root
    ctx.lineTo(-16, 26);  // Keel bulb front
    ctx.lineTo(-8, 26);   // Keel bulb aft
    ctx.lineTo(-4, 16);   // Keel aft
    ctx.lineTo(-26, 12);  // Stern bottom
    ctx.closePath();
    ctx.fillStyle = '#1e293b';
    ctx.fill();
    ctx.strokeStyle = Math.abs(effectivePitch) >= 12 ? '#ff1744' : (Math.abs(effectivePitch) >= 6 ? '#ffb300' : '#00e5ff');
    ctx.lineWidth = 2;
    ctx.stroke();

    // Waterline reference
    ctx.beginPath();
    ctx.moveTo(-36, 6);
    ctx.lineTo(38, 6);
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.3)';
    ctx.setLineDash([2, 2]);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.restore();

    // Digital Readout
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (fault || pitchDeg === null) {
      ctx.fillStyle = '#ffb300';
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.fillText('---', cx, cy + 34);
    } else {
      ctx.fillStyle = Math.abs(pitchDeg) >= 12 ? '#ff1744' : (Math.abs(pitchDeg) >= 6 ? '#ffb300' : '#00e5ff');
      ctx.font = 'bold 14px "JetBrains Mono", monospace';
      const dir = pitchDeg > 0.1 ? 'BOW UP' : (pitchDeg < -0.1 ? 'BOW DN' : 'LEVEL');
      ctx.fillText(`${Math.abs(pitchDeg).toFixed(1)}° ${dir}`, cx, cy + 34);
    }
  },

  /**
   * Renders the Heave & Vertical Acceleration Instrument (Вертикальная качка)
   * @param {HTMLCanvasElement} canvas
   * @param {number|null} heaveM Heave displacement in meters
   * @param {number|null} accelZ Vertical acceleration in m/s^2 (nominal 9.81 m/s^2 = 1.0g)
   * @param {boolean} fault Sensor fault state
   */
  drawHeaveGauge(canvas, rawHeaveM, rawAccelZ, fault = false) {
    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    const heaveM = this._smoothLinear('heave', rawHeaveM, dt);
    const accelZ = this._smoothLinear('accelZ', rawAccelZ, dt);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);

    // Bezel
    ctx.beginPath();
    ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
    ctx.fillStyle = '#0a101d';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#1f2d47';
    ctx.stroke();

    // Semi-circular G-Meter Arc (0.0g to 2.5g)
    const startRad = Math.PI * 0.75;
    const endRad = Math.PI * 2.25;

    // Normal green zone (0.7g - 1.3g)
    const normStart = startRad + (0.7 / 2.5) * (endRad - startRad);
    const normEnd = startRad + (1.3 / 2.5) * (endRad - startRad);
    ctx.beginPath();
    ctx.arc(cx, cy, r, normStart, normEnd);
    ctx.strokeStyle = 'rgba(0, 230, 118, 0.5)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Warning amber zone (1.3g - 1.8g)
    const warnEnd = startRad + (1.8 / 2.5) * (endRad - startRad);
    ctx.beginPath();
    ctx.arc(cx, cy, r, normEnd, warnEnd);
    ctx.strokeStyle = 'rgba(255, 179, 0, 0.6)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Danger red zone (1.8g - 2.5g)
    ctx.beginPath();
    ctx.arc(cx, cy, r, warnEnd, endRad);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.7)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Ticks: 0.0g, 0.5g, 1.0g, 1.5g, 2.0g, 2.5g
    for (let g = 0.0; g <= 2.51; g += 0.5) {
      const frac = g / 2.5;
      const rad = startRad + frac * (endRad - startRad);
      const isMajor = Math.abs(g - 1.0) < 0.01 || g === 0.0 || g === 2.0;
      const innerR = isMajor ? r - 10 : r - 5;

      const x1 = cx + Math.cos(rad) * r;
      const y1 = cy + Math.sin(rad) * r;
      const x2 = cx + Math.cos(rad) * innerR;
      const y2 = cy + Math.sin(rad) * innerR;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = g === 1.0 ? '#00e5ff' : '#94a3b8';
      ctx.lineWidth = isMajor ? 2 : 1;
      ctx.stroke();

      const textR = r - 18;
      const tx = cx + Math.cos(rad) * textR;
      const ty = cy + Math.sin(rad) * textR;
      ctx.fillStyle = g === 1.0 ? '#00e5ff' : '#94a3b8';
      ctx.font = '8px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${g.toFixed(1)}g`, tx, ty);
    }

    // Needle for vertical G-force
    const gVal = (fault || accelZ === null) ? 1.0 : Math.max(0.0, Math.min(2.5, accelZ / 9.80665));
    const needleRad = startRad + (gVal / 2.5) * (endRad - startRad);

    if (!fault && accelZ !== null) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(needleRad);

      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(r - 12, 0);
      ctx.strokeStyle = gVal >= 1.8 ? '#ff1744' : (gVal >= 1.3 ? '#ffb300' : '#00e5ff');
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#00e5ff';
      ctx.fill();

      ctx.restore();
    }

    // Center Heave Height & G Readout
    ctx.beginPath();
    ctx.arc(cx, cy + 12, 28, 0, Math.PI * 2);
    ctx.fillStyle = '#111827';
    ctx.fill();
    ctx.strokeStyle = '#1f2d47';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (fault || accelZ === null) {
      ctx.fillStyle = '#ffb300';
      ctx.font = 'bold 12px "JetBrains Mono", monospace';
      ctx.fillText('---', cx, cy + 8);
    } else {
      ctx.fillStyle = gVal >= 1.8 ? '#ff1744' : (gVal >= 1.3 ? '#ffb300' : '#00e5ff');
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.fillText(`${gVal.toFixed(2)} g`, cx, cy + 6);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '9px "Inter", sans-serif';
      const hStr = heaveM !== null ? `${heaveM.toFixed(2)}m` : '0.0m';
      ctx.fillText(`HEAVE ${hStr}`, cx, cy + 18);
    }
  },

  /**
   * Renders the Slamming & Hull Shock Meter (Индикатор слеминга)
   * @param {HTMLCanvasElement} canvas
   * @param {number} slamForceKn Active slamming force in kN
   * @param {boolean} isSlamming Slamming active flag
   * @param {number} peakSlamKn Max peak slamming force recorded
   * @param {boolean} fault Sensor fault state
   */
  drawSlammingGauge(canvas, rawSlamForceKn = 0.0, isSlamming = false, peakSlamKn = 12.0, fault = false) {
    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    const slamForceKn = this._smoothLinear('slam', rawSlamForceKn, dt);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 14;

    ctx.clearRect(0, 0, w, h);

    // Bezel
    ctx.beginPath();
    ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
    ctx.fillStyle = isSlamming ? '#1a0d14' : '#0a101d';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = isSlamming ? '#ff1744' : '#1f2d47';
    ctx.stroke();

    // Slamming Shock Pulse Ring when active
    if (isSlamming) {
      ctx.beginPath();
      ctx.arc(cx, cy, r - 4, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255, 23, 68, 0.6)';
      ctx.lineWidth = 4;
      ctx.stroke();
    }

    // Arc Scale (0 to 25 kN)
    const startRad = Math.PI * 0.8;
    const endRad = Math.PI * 2.2;
    const forceRatio = Math.min(1.0, Math.max(0.0, slamForceKn / 25.0));

    // Background track
    ctx.beginPath();
    ctx.arc(cx, cy, r, startRad, endRad);
    ctx.strokeStyle = 'rgba(31, 45, 71, 0.6)';
    ctx.lineWidth = 8;
    ctx.stroke();

    // Active Force Arc
    if (forceRatio > 0.01) {
      const activeEnd = startRad + forceRatio * (endRad - startRad);
      ctx.beginPath();
      ctx.arc(cx, cy, r, startRad, activeEnd);
      ctx.strokeStyle = slamForceKn > 10.0 ? '#ff1744' : (slamForceKn > 4.0 ? '#ffb300' : '#00e676');
      ctx.lineWidth = 8;
      ctx.stroke();
    }

    // Impact Ticks: 0, 5, 10, 15, 20, 25 kN
    for (let f = 0; f <= 25; f += 5) {
      const frac = f / 25.0;
      const rad = startRad + frac * (endRad - startRad);
      const isMajor = f % 10 === 0;
      const innerR = isMajor ? r - 10 : r - 6;

      const x1 = cx + Math.cos(rad) * r;
      const y1 = cy + Math.sin(rad) * r;
      const x2 = cx + Math.cos(rad) * innerR;
      const y2 = cy + Math.sin(rad) * innerR;

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = f >= 15 ? '#ff1744' : (f >= 10 ? '#ffb300' : '#94a3b8');
      ctx.lineWidth = isMajor ? 2 : 1;
      ctx.stroke();

      if (isMajor) {
        const textR = r - 18;
        const tx = cx + Math.cos(rad) * textR;
        const ty = cy + Math.sin(rad) * textR;
        ctx.fillStyle = '#94a3b8';
        ctx.font = '8px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${f}k`, tx, ty);
      }
    }

    // Center Display
    ctx.beginPath();
    ctx.arc(cx, cy, 32, 0, Math.PI * 2);
    ctx.fillStyle = '#111827';
    ctx.fill();
    ctx.strokeStyle = isSlamming ? '#ff1744' : '#1f2d47';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (isSlamming || slamForceKn > 0.5) {
      ctx.fillStyle = slamForceKn > 10.0 ? '#ff1744' : '#ffb300';
      ctx.font = 'bold 15px "JetBrains Mono", monospace';
      ctx.fillText(`${slamForceKn.toFixed(1)}`, cx, cy - 6);
      ctx.fillStyle = '#f87171';
      ctx.font = 'bold 9px "Inter", sans-serif';
      ctx.fillText(slamForceKn > 10.0 ? 'IMPACT SLAM' : 'WAVE SHOCK', cx, cy + 10);
    } else {
      ctx.fillStyle = '#00e676';
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.fillText('0.0 kN', cx, cy - 4);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '8px "Inter", sans-serif';
      ctx.fillText('NO SLAM', cx, cy + 10);
    }
  }
};
