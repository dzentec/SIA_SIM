/**
 * High-Performance Marine Canvas Dial Instruments (60 FPS)
 * Strict conformance with authentic Raymarine / B&G Marine Instruments
 */

const InstrumentRenderer = {

  /**
   * Renders the Apparent Wind (AWA / AWS) Marine Gauge
   * @param {HTMLCanvasElement} canvas
   * @param {number|null} awa Apparent Wind Angle (-180 to +180)
   * @param {number|null} aws Apparent Wind Speed in knots
   * @param {boolean} fault Sensor fault state
   */
  drawWindDial(canvas, awa, aws, fault = false) {
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
    // Port sector: -Math.PI/2 to Math.PI/2 (Left side)
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2, true);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.4)';
    ctx.lineWidth = 6;
    ctx.stroke();

    // Starboard sector: -Math.PI/2 to Math.PI/2 (Right side)
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

    // Needle Pointer
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
  drawHeelDial(canvas, heel, fault = false) {
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
  drawNavDial(canvas, cog, sog, fault = false) {
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
  }
};
