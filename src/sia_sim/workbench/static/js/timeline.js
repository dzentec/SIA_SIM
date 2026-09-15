/**
 * Multi-Track Temporal Debugger & Timeline Scrubber (100 Hz Step Synchronization)
 */

const TimelineRenderer = {
  canvas: null,
  ctx: null,
  cursor: null,
  container: null,
  data: null,
  isDragging: false,

  init(data) {
    this.data = data;
    this.canvas = document.getElementById('timelineCanvas');
    this.ctx = this.canvas.getContext('2d');
    this.cursor = document.getElementById('timelineCursor');
    this.container = document.getElementById('timelineContainer');

    this.bindEvents();
    this.renderTracks();
  },

  bindEvents() {
    if (this._eventsBound) return;
    this._eventsBound = true;

    const handleScrub = (e) => {
      if (!this.data || !this.data.ticks || this.data.ticks.length === 0) return;
      const rect = this.canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
      const ratio = x / rect.width;
      const targetTick = Math.floor(ratio * (this.data.ticks.length - 1));
      
      if (window.AppState) {
        window.AppState.currentTick = targetTick;
        if (window.renderTick) {
          window.renderTick(targetTick);
        }
      }
    };

    this.container.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      handleScrub(e);
    });

    window.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        handleScrub(e);
      }
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    // Touch support
    this.container.addEventListener('touchstart', (e) => {
      this.isDragging = true;
      handleScrub(e);
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (this.isDragging) {
        handleScrub(e);
      }
    }, { passive: true });

    window.addEventListener('touchend', () => {
      this.isDragging = false;
    });
  },

  updateCursor(currentTick, totalTicks) {
    if (!this.cursor || totalTicks <= 0) return;
    const pct = (currentTick / (totalTicks - 1)) * 100;
    this.cursor.style.left = `${pct}%`;
  },

  renderTracks() {
    if (!this.canvas || !this.ctx || !this.data) return;

    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const totalTicks = this.data.ticks.length;
    if (totalTicks === 0) return;

    ctx.clearRect(0, 0, w, h);

    // Track Backgrounds
    ctx.fillStyle = '#060a12';
    ctx.fillRect(0, 0, w, h);

    // Grid Lines & Time Ruler (every 2 seconds = 200 ticks)
    const durationS = this.data.duration_ms / 1000;
    const pxPerSec = w / durationS;

    for (let sec = 0; sec <= durationS; sec += 2) {
      const x = sec * pxPerSec;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.strokeStyle = sec % 5 === 0 ? 'rgba(31, 45, 71, 0.8)' : 'rgba(31, 45, 71, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();

      if (sec % 5 === 0) {
        ctx.fillStyle = '#64748b';
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`00:${sec.toString().padStart(2, '0')}`, x + 4, 12);
      }
    }

    // Track 1: Event Spans (Wind Gusts & Waves)
    const trackY1 = 20;
    const trackH1 = 14;

    for (let i = 0; i < totalTicks; i++) {
      const tick = this.data.ticks[i];
      const x = (i / totalTicks) * w;
      const stepW = Math.max(1, w / totalTicks);

      // Wind Gusts (Amber)
      if (tick.ground_truth.tws_kt > 15.5) {
        ctx.fillStyle = 'rgba(255, 179, 0, 0.7)';
        ctx.fillRect(x, trackY1, stepW, trackH1);
      }

      // Wave Impacts (Blue)
      if (tick.ground_truth.wave_impact_active) {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.85)';
        ctx.fillRect(x, trackY1 + 18, stepW, trackH1);
      }

      // SIA Decisions (Cyan)
      if (tick.sia_decision.selected_response !== null) {
        ctx.fillStyle = 'rgba(0, 229, 255, 0.7)';
        ctx.fillRect(x, trackY1 + 36, stepW, trackH1);
      }
    }

    // Track Labels
    ctx.fillStyle = '#94a3b8';
    ctx.font = '9px "Inter", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('WIND GUSTS', 6, trackY1 + 10);
    ctx.fillText('WAVE IMPACTS', 6, trackY1 + 28);
    ctx.fillText('SIA ADVISORY', 6, trackY1 + 46);

    // Track 4: True Heel Curve (Green -> Amber -> Red)
    ctx.beginPath();
    for (let i = 0; i < totalTicks; i++) {
      const tick = this.data.ticks[i];
      const heel = Math.abs(tick.ground_truth.heel_deg);
      const x = (i / totalTicks) * w;
      // Map heel 0..35 deg to height 90..60 px
      const y = 92 - Math.min(32, (heel / 35.0) * 32);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.strokeStyle = '#00e676';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Critical threshold line at 25 deg
    const critY = 92 - (25.0 / 35.0) * 32;
    ctx.beginPath();
    ctx.moveTo(0, critY);
    ctx.lineTo(w, critY);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.5)';
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);
  }
};

window.TimelineRenderer = TimelineRenderer;
