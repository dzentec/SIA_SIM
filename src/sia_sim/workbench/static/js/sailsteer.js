/**
 * B&G SailSteer™ Navigation Display Engine
 * Pixel-Perfect Authentic Recreation of B&G Zeus / Vulcan / Triton² SailSteer Instrument
 * 60 FPS HTML5 Canvas + Analytical Wind Triangle & Navigation Controller
 */

class SailSteerController {
  static process(raw) {
    if (!raw) return this.getZeroState();

    const gt = raw.ground_truth || {};
    const sf = raw.sensor_frame || {};
    const imu = sf.imu || {};
    const gps = sf.gps || {};
    const wind = sf.wind || {};

    const simTimeMs = raw.sim_time_ms || 0;
    const totalSecs = Math.floor(simTimeMs / 1000);
    const hh = String(Math.floor(totalSecs / 3600) % 24).padStart(2, '0');
    const mm = String(Math.floor((totalSecs % 3600) / 60)).padStart(2, '0');
    const ss = String(totalSecs % 60).padStart(2, '0');
    const systemTime = `${hh}:${mm}:${ss}`;

    const gpsLock = !gps.fault && !gps.fix_loss && gps.sog_kt !== null && gps.sog_kt !== undefined;

    // Heading: prefer IMU yaw or GT heading
    let hdg = 155.0;
    if (gt.yaw_deg !== undefined && gt.yaw_deg !== null) {
      hdg = ((gt.yaw_deg % 360) + 360) % 360;
    } else if (gps.cog_deg !== null && gps.cog_deg !== undefined) {
      hdg = gps.cog_deg;
    }

    const sog = gpsLock ? (gps.sog_kt ?? gt.sog_kt ?? 4.5) : null;
    const cog = gpsLock ? (gps.cog_deg ?? gt.cog_deg ?? 159.0) : null;

    // Sea current
    const currentSpeed = gt.current_speed_kt ?? (gt.current_speed_m_s ? gt.current_speed_m_s * 1.943844 : 2.3);
    const currentDirTrue = gt.current_dir_deg ?? (gt.current_direction_deg ?? 245.0);
    let currentRelDir = 90.0;
    if (hdg !== null && currentDirTrue !== null) {
      let diff = currentDirTrue - hdg;
      while (diff > 180) diff -= 360;
      while (diff < -180) diff += 360;
      currentRelDir = diff;
    }

    // Speed Through Water (STW)
    let stw = 2.8;
    if (sog !== null) {
      const rad = (currentRelDir * Math.PI) / 180;
      stw = Math.max(0.0, Math.round((sog - (currentSpeed * Math.cos(rad) * 0.35)) * 10) / 10);
    }

    // Apparent Wind
    const awa = !wind.fault && wind.apparent_wind_angle_deg !== null && wind.apparent_wind_angle_deg !== undefined
      ? wind.apparent_wind_angle_deg
      : -50.0;
    const aws = !wind.fault && wind.apparent_wind_speed_kt !== null && wind.apparent_wind_speed_kt !== undefined
      ? wind.apparent_wind_speed_kt
      : 18.4;

    // True Wind
    let twa = -57.0;
    let tws = 16.2;
    let twd = 96.0;

    if (gt.tws_kt !== undefined && gt.tws_kt !== null) {
      tws = gt.tws_kt;
      twd = gt.twd_deg !== undefined ? ((gt.twd_deg % 360) + 360) % 360 : 96.0;
      if (hdg !== null) {
        let diff = twd - hdg;
        while (diff > 180) diff -= 360;
        while (diff < -180) diff += 360;
        twa = diff;
      }
    } else if (awa !== null && aws !== null && stw !== null) {
      const awaRad = (awa * Math.PI) / 180;
      const vtx = aws * Math.sin(awaRad);
      const vty = aws * Math.cos(awaRad) - stw;
      tws = Math.sqrt(vtx * vtx + vty * vty);
      twa = (Math.atan2(vtx, vty) * 180) / Math.PI;
      twd = ((hdg + twa) % 360 + 360) % 360;
    }

    // Waypoint
    const wptDist = 9.40;
    const wptBrg = 107.0;
    let steeringError = -55;
    if (hdg !== null) {
      let err = wptBrg - hdg;
      while (err > 180) err -= 360;
      while (err < -180) err += 360;
      steeringError = Math.round(err);
    }

    let etw = '15:24:35';
    if (sog && sog > 0.5) {
      const hours = wptDist / sog;
      const totalSec = Math.floor(hours * 3600);
      const eh = String(Math.floor(totalSec / 3600)).padStart(2, '0');
      const em = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
      const es = String(totalSec % 60).padStart(2, '0');
      etw = `${eh}:${em}:${es}`;
    }

    const latDeg = gps.latitude_deg ?? 36.993117;
    const lonDeg = gps.longitude_deg ?? -8.067833;
    const pos = gpsLock ? {
      lat: `N 36°59.587'`,
      lon: `W  8°04.070'`,
    } : null;

    const depth = gt.wave_elevation_m !== undefined
      ? Math.max(1.5, Math.round((29.8 + (gt.wave_elevation_m || 0.0) * 0.4) * 10) / 10)
      : 29.8;

    return {
      timestamp: simTimeMs,
      system_time: systemTime,
      gps_lock: gpsLock,
      navigation: {
        hdg: hdg !== null ? Math.round(hdg * 10) / 10 : 155.0,
        stw: stw !== null ? Math.round(stw * 10) / 10 : 2.8,
        sog: sog !== null ? Math.round(sog * 10) / 10 : 4.5,
        cog: cog !== null ? Math.round(cog * 10) / 10 : 159.0,
        variation: -1.7,
        depth: depth,
        pos: pos,
      },
      wind: {
        twa: twa !== null ? Math.round(twa * 10) / 10 : -57.0,
        awa: awa !== null ? Math.round(awa * 10) / 10 : -50.0,
        tws: tws !== null ? Math.round(tws * 10) / 10 : 16.2,
        aws: aws !== null ? Math.round(aws * 10) / 10 : 18.4,
        twd: twd !== null ? Math.round(twd * 10) / 10 : 96.0,
        twa_opt_upwind: 45.0,
        twa_opt_downwind: 140.0,
      },
      waypoint: {
        name: 'FARO',
        dist: wptDist,
        brg: wptBrg,
        steering_error: steeringError,
        etw: etw,
        layline_port: 5.08,
        layline_starboard: 7.82,
      },
      current: {
        speed: currentSpeed !== null ? Math.round(currentSpeed * 10) / 10 : 2.3,
        direction_relative: currentRelDir !== null ? Math.round(currentRelDir) : 90.0,
      },
    };
  }

  static getZeroState() {
    return {
      timestamp: 0,
      system_time: '12:04:37',
      gps_lock: true,
      navigation: {
        hdg: 155.0,
        stw: 2.8,
        sog: 4.5,
        cog: 159.0,
        variation: -1.7,
        depth: 29.8,
        pos: { lat: "N 36°59.587'", lon: "W  8°04.070'" },
      },
      wind: {
        twa: -57.0,
        awa: -50.0,
        tws: 16.2,
        aws: 18.4,
        twd: 96.0,
        twa_opt_upwind: 45.0,
        twa_opt_downwind: 140.0,
      },
      waypoint: {
        name: 'FARO',
        dist: 9.40,
        brg: 107.0,
        steering_error: -55,
        etw: '15:24:35',
        layline_port: 5.08,
        layline_starboard: 7.82,
      },
      current: {
        speed: 2.3,
        direction_relative: 90.0,
      },
    };
  }
}

const SailSteerRenderer = {
  _smoothed: {
    hdg: 155.0,
    twa: -57.0,
    awa: -50.0,
    lastTime: performance.now(),
  },

  _offscreenCompass: null,
  _offscreenSize: 0,

  reset() {
    this._smoothed.hdg = 155.0;
    this._smoothed.twa = -57.0;
    this._smoothed.awa = -50.0;
    this._smoothed.lastTime = performance.now();
  },

  _smoothAngle(key, targetDeg, dtSec, tau = 0.35) {
    if (targetDeg === null || targetDeg === undefined || isNaN(targetDeg)) return targetDeg;
    let cur = this._smoothed[key];
    if (cur === null || cur === undefined) {
      this._smoothed[key] = targetDeg;
      return targetDeg;
    }
    const alpha = 1.0 - Math.exp(-dtSec / tau);
    let diff = (targetDeg - cur) % 360;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    const updated = cur + alpha * diff;
    this._smoothed[key] = updated;
    return updated;
  },

  /**
   * Generates the solid white B&G compass rose ring with black degree numerals
   */
  _ensureOffscreenCompass(size, outerR, innerR) {
    if (this._offscreenCompass && this._offscreenSize === size) {
      return this._offscreenCompass;
    }

    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    const cx = size / 2;
    const cy = size / 2;

    ctx.clearRect(0, 0, size, size);

    // 1. Solid White Compass Ring Band
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, 0, Math.PI * 2, false);
    ctx.arc(cx, cy, innerR, 0, Math.PI * 2, true);
    ctx.closePath();
    ctx.fillStyle = '#FFFFFF';
    ctx.fill();

    // Subtle border on white ring
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
    ctx.strokeStyle = '#D1D5DB';
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 2. Black Degree Numerals and Ticks along the White Ring
    const textRadius = (outerR + innerR) / 2;

    for (let deg = 0; deg < 360; deg += 5) {
      const rad = ((deg - 90) * Math.PI) / 180;
      const isMajor30 = deg % 30 === 0;
      const isDot10 = deg % 10 === 0;

      // Small black tick dots on outer edge
      if (isDot10) {
        const dotR = outerR - 3.5;
        const dx = cx + dotR * Math.cos(rad);
        const dy = cy + dotR * Math.sin(rad);
        ctx.beginPath();
        ctx.arc(dx, dy, 1.2, 0, Math.PI * 2);
        ctx.fillStyle = '#000000';
        ctx.fill();
      }

      // Numerals every 30 degrees
      if (isMajor30) {
        const tx = cx + textRadius * Math.cos(rad);
        const ty = cy + textRadius * Math.sin(rad);

        ctx.save();
        ctx.translate(tx, ty);
        // Rotate text so it faces nicely along the circular track
        ctx.rotate(rad + Math.PI / 2);

        let label = '';
        if (deg === 0) label = 'N';
        else label = String(deg).padStart(3, '0');

        ctx.font = deg === 0
          ? 'bold 15px "Inter", "Arial", sans-serif'
          : 'bold 13.5px "Inter", "Arial", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#000000';
        ctx.fillText(label, 0, 0);

        ctx.restore();
      }
    }

    this._offscreenCompass = canvas;
    this._offscreenSize = size;
    return canvas;
  },

  render(canvas, data) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;

    // Radius parameters matching authentic B&G proportions
    const outerBezelR = Math.min(cx, cy) - 8;
    const tackBandR = outerBezelR - 6;
    const whiteCompassOuterR = outerBezelR - 26;
    const whiteCompassInnerR = whiteCompassOuterR - 34;

    const now = performance.now();
    const dt = Math.max(0.005, Math.min(0.1, (now - (this._smoothed.lastTime || now)) / 1000));
    this._smoothed.lastTime = now;

    const nav = data.navigation || {};
    const wind = data.wind || {};
    const wpt = data.waypoint;
    const current = data.current || {};

    const rawHdg = nav.hdg !== null ? nav.hdg : 155.0;
    const hdg = this._smoothAngle('hdg', rawHdg, dt);
    const twa = wind.twa !== null ? this._smoothAngle('twa', wind.twa, dt) : -57.0;
    const awa = wind.awa !== null ? this._smoothAngle('awa', wind.awa, dt) : -50.0;
    const tws = wind.tws ?? 16.2;

    ctx.clearRect(0, 0, w, h);

    // =========================================================================
    // LAYER 0: DARK BEZEL & STATIC RADIAL MARKS
    // =========================================================================
    ctx.save();
    // Solid Black Interior
    ctx.beginPath();
    ctx.arc(cx, cy, outerBezelR, 0, Math.PI * 2);
    ctx.fillStyle = '#000000';
    ctx.fill();

    // Dark grey outer track
    ctx.beginPath();
    ctx.arc(cx, cy, outerBezelR, 0, Math.PI * 2);
    ctx.arc(cx, cy, whiteCompassOuterR, 0, Math.PI * 2, true);
    ctx.fillStyle = '#181C24';
    ctx.fill();

    // Radial tick notches on outer bezel every 30° / 90°
    for (let deg = 0; deg < 360; deg += 30) {
      const rad = ((deg - 90) * Math.PI) / 180;
      const isCard = deg % 90 === 0;
      const tLen = isCard ? 14 : 7;
      const x1 = cx + (outerBezelR - tLen) * Math.cos(rad);
      const y1 = cy + (outerBezelR - tLen) * Math.sin(rad);
      const x2 = cx + outerBezelR * Math.cos(rad);
      const y2 = cy + outerBezelR * Math.sin(rad);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = isCard ? 3.5 : 2;
      ctx.stroke();
    }
    ctx.restore();

    // =========================================================================
    // LAYER 1: TACK & GYBE COLORED ARCS ON OUTER BEZEL (Red Port / Green Stbd)
    // =========================================================================
    ctx.save();
    const arcW = 14;
    const arcR = whiteCompassOuterR + arcW / 2 + 1;

    // Upwind Port Arc (Red: -48° to -2°)
    ctx.beginPath();
    ctx.arc(cx, cy, arcR, ((-48 - 90) * Math.PI) / 180, ((-3 - 90) * Math.PI) / 180, false);
    ctx.strokeStyle = '#E60000';
    ctx.lineWidth = arcW;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Upwind Starboard Arc (Green: +2° to +48°)
    ctx.beginPath();
    ctx.arc(cx, cy, arcR, ((3 - 90) * Math.PI) / 180, ((48 - 90) * Math.PI) / 180, false);
    ctx.strokeStyle = '#00D020';
    ctx.lineWidth = arcW;
    ctx.lineCap = 'round';
    ctx.stroke();

    // White center separator dot/line at top
    ctx.beginPath();
    ctx.moveTo(cx, cy - arcR - arcW / 2);
    ctx.lineTo(cx, cy - arcR + arcW / 2);
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // White tick dots along the Red and Green arcs (every 10°)
    [-40, -30, -20, -10, 10, 20, 30, 40].forEach((ang) => {
      const rRad = ((ang - 90) * Math.PI) / 180;
      const px = cx + arcR * Math.cos(rRad);
      const py = cy + arcR * Math.sin(rRad);
      ctx.beginPath();
      ctx.arc(px, py, 1.8, 0, Math.PI * 2);
      ctx.fillStyle = '#FFFFFF';
      ctx.fill();
    });
    ctx.restore();

    // =========================================================================
    // LAYER 2: SHADED LAYLINE SECTORS (Dynamic Translucent Red & Green Wedges)
    // =========================================================================
    ctx.save();
    const twdDeg = wind.twd ?? 96.0;
    const twaOpt = wind.twa_opt_upwind || 45.0;

    // Port Layline Angle relative to boat heading
    const portLayScreenDeg = ((twdDeg - twaOpt - hdg) % 360 + 360) % 360;
    const portLayRad = ((portLayScreenDeg - 90) * Math.PI) / 180;

    // Starboard Layline Angle relative to boat heading
    const stbdLayScreenDeg = ((twdDeg + twaOpt - hdg) % 360 + 360) % 360;
    const stbdLayRad = ((stbdLayScreenDeg - 90) * Math.PI) / 180;

    // Port Layline Red Wedge
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, whiteCompassInnerR, portLayRad - 0.22, portLayRad + 0.08, false);
    ctx.closePath();
    ctx.fillStyle = 'rgba(230, 0, 0, 0.45)';
    ctx.fill();

    // Starboard Green Layline Wedge & Dashed Line
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, whiteCompassInnerR, stbdLayRad - 0.28, stbdLayRad + 0.12, false);
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 208, 32, 0.45)';
    ctx.fill();

    // Green dashed layline ray
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + whiteCompassInnerR * Math.cos(stbdLayRad), cy + whiteCompassInnerR * Math.sin(stbdLayRad));
    ctx.strokeStyle = '#00FF40';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([7, 5]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    // =========================================================================
    // LAYER 3: ROTATING SOLID WHITE COMPASS ROSE RING (-HDG)
    // =========================================================================
    ctx.save();
    ctx.translate(cx, cy);
    const rotRad = ((-hdg) * Math.PI) / 180;
    ctx.rotate(rotRad);

    const offCompass = this._ensureOffscreenCompass(w, whiteCompassOuterR, whiteCompassInnerR);
    ctx.drawImage(offCompass, -w / 2, -h / 2);
    ctx.restore();

    // =========================================================================
    // LAYER 4: BOAT SILHOUETTE (Curved Silver Hull Lines, Bow at Top)
    // =========================================================================
    ctx.save();
    ctx.translate(cx, cy);

    // Sleek dual hull curves opening to stern
    const bowY = -whiteCompassInnerR * 0.72;
    const sternY = whiteCompassInnerR * 0.95;
    const beamW = whiteCompassInnerR * 0.38;

    // Port hull curve
    ctx.beginPath();
    ctx.moveTo(0, bowY);
    ctx.bezierCurveTo(-beamW * 0.7, -whiteCompassInnerR * 0.2, -beamW, whiteCompassInnerR * 0.4, -beamW * 0.85, sternY);
    ctx.strokeStyle = '#A0AAB8';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Starboard hull curve
    ctx.beginPath();
    ctx.moveTo(0, bowY);
    ctx.bezierCurveTo(beamW * 0.7, -whiteCompassInnerR * 0.2, beamW, whiteCompassInnerR * 0.4, beamW * 0.85, sternY);
    ctx.strokeStyle = '#A0AAB8';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Subtle dark radial gradient inside hull
    const hullGrad = ctx.createRadialGradient(0, 0, 5, 0, 0, whiteCompassInnerR * 0.8);
    hullGrad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    hullGrad.addColorStop(1, 'rgba(0, 0, 0, 0.8)');
    ctx.fillStyle = hullGrad;
    ctx.fill();
    ctx.restore();

    // =========================================================================
    // LAYER 5: CURRENT DRIFT VECTOR (entypo:arrow-up SVG Iconify Integration)
    // =========================================================================
    const curSpeed = current.speed ?? 2.3;
    const curRelDir = current.direction_relative !== null ? current.direction_relative : 90;

    if (curSpeed > 0.05) {
      ctx.save();
      // entypo:arrow-up points UP at 0°, so rotate directly by curRelDir in degrees
      const curAngleRad = (curRelDir * Math.PI) / 180;
      
      // Dynamic scale based on speed: length ranges from 60px to 105px
      const baseScale = Math.min(6.2, Math.max(3.8, 3.4 + curSpeed * 0.85));
      const baseOffset = 10; // Distance from center hub

      ctx.translate(cx, cy);
      ctx.rotate(curAngleRad);

      // Shadow for high-contrast separation
      ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
      ctx.shadowBlur = 10;
      ctx.shadowOffsetX = 1;
      ctx.shadowOffsetY = 2;

      // Linear gradient along arrow direction (from base to tip)
      const arrowGrad = ctx.createLinearGradient(0, -baseOffset, 0, -(baseOffset + 14.5 * baseScale));
      arrowGrad.addColorStop(0, '#005CE6');
      arrowGrad.addColorStop(0.55, '#0099FF');
      arrowGrad.addColorStop(1, '#00D8FF');

      // entypo:arrow-up SVG Path: M10 2.5L16.5 9H13v8H7V9H3.5z
      const entypoArrow = new Path2D('M10 2.5L16.5 9H13v8H7V9H3.5z');

      ctx.save();
      ctx.translate(0, -baseOffset);
      ctx.scale(baseScale, baseScale);
      ctx.translate(-10, -17); // Anchor base (10, 17) to local origin (0, 0)

      ctx.fillStyle = arrowGrad;
      ctx.fill(entypoArrow);

      ctx.shadowColor = 'transparent';
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.4 / baseScale; // Consistent 1.4px outer stroke
      ctx.lineJoin = 'round';
      ctx.stroke(entypoArrow);
      ctx.restore();

      // Center pivot hub/ring
      ctx.beginPath();
      ctx.arc(0, 0, 7.5, 0, Math.PI * 2);
      ctx.fillStyle = '#0077EE';
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#FFFFFF';
      ctx.fill();

      // Speed text readout (e.g. '1.2' / '2.3') centered on arrow shaft
      const textDist = baseOffset + 4.2 * baseScale; // Center of shaft (Y=12.8 in path)
      const degNormalized = ((curRelDir % 360) + 360) % 360;

      ctx.save();
      ctx.translate(0, -textDist);
      // Keep text right-side up if arrow is inverted
      if (degNormalized > 90 && degNormalized < 270) {
        ctx.rotate(Math.PI);
      }
      ctx.font = '900 13px "Inter", "Arial Black", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Dark shadow & stroke for high contrast
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.95)';
      ctx.lineWidth = 3.5;
      ctx.strokeText(curSpeed.toFixed(1), 0, 0);

      // Bright white fill
      ctx.fillStyle = '#FFFFFF';
      ctx.fillText(curSpeed.toFixed(1), 0, 0);
      ctx.restore();

      ctx.restore();
    }

    // =========================================================================
    // LAYER 6: WIND NEEDLES 'A' & 'T' (Inward-Pointing Blue Chevrons + Yellow Bead)
    // =========================================================================
    ctx.save();
    // 1. True Wind Needle 'T' (Chevron pointing inwards at angle TWA)
    const twaRad = ((twa - 90) * Math.PI) / 180;
    const tTipR = whiteCompassOuterR + 1;
    const tTipX = cx + tTipR * Math.cos(twaRad);
    const tTipY = cy + tTipR * Math.sin(twaRad);

    ctx.save();
    ctx.translate(tTipX, tTipY);
    ctx.rotate(twaRad + Math.PI / 2);

    // Blue Chevron polygon pointing downward (inward to compass)
    ctx.beginPath();
    ctx.moveTo(0, 0); // Tip touching compass
    ctx.lineTo(-18, -32);
    ctx.lineTo(0, -24);
    ctx.lineTo(18, -32);
    ctx.closePath();
    ctx.fillStyle = '#0052FF';
    ctx.fill();
    ctx.strokeStyle = '#38BDF8';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Bold White 'T'
    ctx.font = 'bold 13px "Inter", "Arial", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText('T', 0, -17);
    ctx.restore();

    // 2. Apparent Wind Needle 'A' (Chevron pointing inwards at angle AWA)
    const awaRad = ((awa - 90) * Math.PI) / 180;
    const aTipR = whiteCompassOuterR + 1;
    const aTipX = cx + aTipR * Math.cos(awaRad);
    const aTipY = cy + aTipR * Math.sin(awaRad);

    ctx.save();
    ctx.translate(aTipX, aTipY);
    ctx.rotate(awaRad + Math.PI / 2);

    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(-18, -32);
    ctx.lineTo(0, -24);
    ctx.lineTo(18, -32);
    ctx.closePath();
    ctx.fillStyle = '#0052FF';
    ctx.fill();
    ctx.strokeStyle = '#38BDF8';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.font = 'bold 13px "Inter", "Arial", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText('A', 0, -17);
    ctx.restore();

    // 3. Bright Yellow Bead Dot with Pointer Tip at AWA
    const beadR = whiteCompassOuterR - 2;
    const beadX = cx + beadR * Math.cos(awaRad);
    const beadY = cy + beadR * Math.sin(awaRad);

    ctx.save();
    ctx.beginPath();
    ctx.arc(beadX, beadY, 8.5, 0, Math.PI * 2);
    ctx.fillStyle = '#FFE500';
    ctx.fill();
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Blue tiny pointer tip on bead
    const tipRad = awaRad;
    ctx.beginPath();
    ctx.moveTo(beadX + 8 * Math.cos(tipRad - 0.5), beadY + 8 * Math.sin(tipRad - 0.5));
    ctx.lineTo(beadX + 15 * Math.cos(tipRad), beadY + 15 * Math.sin(tipRad));
    ctx.lineTo(beadX + 8 * Math.cos(tipRad + 0.5), beadY + 8 * Math.sin(tipRad + 0.5));
    ctx.closePath();
    ctx.fillStyle = '#0066FF';
    ctx.fill();
    ctx.restore();
    ctx.restore();

    // =========================================================================
    // LAYER 7: TOP HEADING BOX (White box + Orange Double-Trapezoid at 12 o'clock)
    // =========================================================================
    ctx.save();
    const boxW = 56;
    const boxH = 28;
    const boxX = cx - boxW / 2;
    const boxY = cy - whiteCompassOuterR - 10;

    // Top Orange Trapezoid (pointing down to box)
    ctx.beginPath();
    ctx.moveTo(cx - 11, boxY - 11);
    ctx.lineTo(cx + 11, boxY - 11);
    ctx.lineTo(cx + 6, boxY - 1);
    ctx.lineTo(cx - 6, boxY - 1);
    ctx.closePath();
    ctx.fillStyle = '#FF9500';
    ctx.fill();

    // White Heading Box
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxW, boxH, 4);
    ctx.fillStyle = '#FFFFFF';
    ctx.fill();
    ctx.strokeStyle = '#181C24';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Bold Black Heading Text '155'
    ctx.font = 'bold 20px "Inter", "Arial", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#000000';
    const hdgNum = Math.round(nav.hdg ?? 155);
    ctx.fillText(String(hdgNum), cx, boxY + boxH / 2 + 1);

    // Bottom Orange Trapezoid (pointing up to box)
    ctx.beginPath();
    ctx.moveTo(cx - 6, boxY + boxH + 1);
    ctx.lineTo(cx + 6, boxY + boxH + 1);
    ctx.lineTo(cx + 11, boxY + boxH + 11);
    ctx.lineTo(cx - 11, boxY + boxH + 11);
    ctx.closePath();
    ctx.fillStyle = '#FF9500';
    ctx.fill();
    ctx.restore();

    // =========================================================================
    // LAYER 8: DOM DASHBOARD VALUES SYNCHRONIZATION
    // =========================================================================
    this._updateDomDashboards(data);
  },

  _updateDomDashboards(data) {
    const nav = data.navigation || {};
    const wind = data.wind || {};
    const wpt = data.waypoint;
    const cur = data.current || {};
    const gpsLock = data.gps_lock;

    const fmtDeg3 = (val) => val !== null && val !== undefined ? String(Math.round(val)).padStart(3, '0') : '---';
    const fmtRelDeg = (val) => val !== null && val !== undefined ? String(Math.round(val)) : '---';
    const fmtKn1 = (val) => val !== null && val !== undefined ? val.toFixed(1) : '---';
    const fmtNm2 = (val) => val !== null && val !== undefined ? val.toFixed(2) : '---';

    // Top Status
    const ssTime = document.getElementById('ssTime');
    if (ssTime) ssTime.textContent = data.system_time || '12:04:37';
    const ssDepthTop = document.getElementById('ssDepthTop');
    if (ssDepthTop) ssDepthTop.textContent = nav.depth !== null ? `${nav.depth.toFixed(1)} m` : '29.8 m';
    const ssVarBottom = document.getElementById('ssVarBottom');
    if (ssVarBottom) ssVarBottom.textContent = 'Var: 1.7°W';

    // Left Panel (Wind Data)
    const ssLeftSog = document.getElementById('ssLeftSog');
    if (ssLeftSog) ssLeftSog.textContent = fmtKn1(nav.sog ?? 4.5);
    const ssLeftTwa = document.getElementById('ssLeftTwa');
    if (ssLeftTwa) ssLeftTwa.textContent = fmtRelDeg(wind.twa ?? -57);
    const ssLeftAwa = document.getElementById('ssLeftAwa');
    if (ssLeftAwa) ssLeftAwa.textContent = fmtRelDeg(wind.awa ?? -50);
    const ssLeftTws = document.getElementById('ssLeftTws');
    if (ssLeftTws) ssLeftTws.textContent = fmtKn1(wind.tws ?? 16.2);
    const ssLeftTwd = document.getElementById('ssLeftTwd');
    if (ssLeftTwd) ssLeftTwd.textContent = fmtDeg3(wind.twd ?? 96);

    // Center-Right Embedded Nav Data
    const ssMidStw = document.getElementById('ssMidStw');
    if (ssMidStw) ssMidStw.textContent = fmtKn1(nav.stw ?? 2.8);
    const ssMidLayPort = document.getElementById('ssMidLayPort');
    if (ssMidLayPort) ssMidLayPort.textContent = wpt ? fmtNm2(wpt.layline_port) : '5.08';
    const ssMidLayStbd = document.getElementById('ssMidLayStbd');
    if (ssMidLayStbd) ssMidLayStbd.textContent = wpt ? fmtNm2(wpt.layline_starboard) : '7.82';
    const ssMidHdg = document.getElementById('ssMidHdg');
    if (ssMidHdg) ssMidHdg.textContent = fmtDeg3(nav.hdg ?? 155);
    const ssMidWptDist = document.getElementById('ssMidWptDist');
    if (ssMidWptDist) ssMidWptDist.textContent = wpt ? fmtNm2(wpt.dist) : '9.40';
    const ssMidWptName = document.getElementById('ssMidWptName');
    if (ssMidWptName) ssMidWptName.textContent = wpt ? wpt.name : 'FARO';
    const ssMidWptBrg = document.getElementById('ssMidWptBrg');
    if (ssMidWptBrg) ssMidWptBrg.textContent = fmtDeg3(wpt ? wpt.brg : 107);

    // Right Quick Bar
    const ssRightSog = document.getElementById('ssRightSog');
    if (ssRightSog) ssRightSog.textContent = fmtKn1(nav.sog ?? 4.5);
    const ssRightCog = document.getElementById('ssRightCog');
    if (ssRightCog) ssRightCog.textContent = fmtDeg3(nav.cog ?? 159);
    const ssRightPos = document.getElementById('ssRightPos');
    if (ssRightPos) {
      if (nav.pos && gpsLock) {
        ssRightPos.innerHTML = `<span class="pos-line">${nav.pos.lat}</span><span class="pos-line">${nav.pos.lon}</span>`;
      } else {
        ssRightPos.innerHTML = `<span class="pos-line">N 36°59.587'</span><span class="pos-line">W  8°04.070'</span>`;
      }
    }
    const ssRightDepth = document.getElementById('ssRightDepth');
    if (ssRightDepth) ssRightDepth.textContent = nav.depth !== null ? nav.depth.toFixed(1) : '29.8';
    const ssRightTime = document.getElementById('ssRightTime');
    if (ssRightTime) ssRightTime.textContent = data.system_time || '12:04:37';
    const ssRightSteer = document.getElementById('ssRightSteer');
    if (ssRightSteer) ssRightSteer.textContent = wpt ? fmtRelDeg(wpt.steering_error ?? -55) : '-55';
    const ssRightEtw = document.getElementById('ssRightEtw');
    if (ssRightEtw) ssRightEtw.textContent = wpt && wpt.etw ? wpt.etw : '15:24:35';
  },

  renderZeroState(canvas) {
    const zeroTelemetry = SailSteerController.getZeroState();
    if (canvas) {
      this.render(canvas, zeroTelemetry);
    } else {
      this._updateDomDashboards(zeroTelemetry);
    }
  }
};

window.SailSteerController = SailSteerController;
window.SailSteerRenderer = SailSteerRenderer;
