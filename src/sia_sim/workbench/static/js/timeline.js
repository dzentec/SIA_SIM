/**
 * Multi-Track Temporal Debugger, Zoomable Canvas & Event Builder
 */

const TimelineRenderer = {
  canvas: null,
  ctx: null,
  cursor: null,
  container: null,
  data: null,
  events: [], // Custom / active scenario events
  activeTool: null, // 'wind_gust' | 'wave_impact' | 'sensor_fault' | null
  zoomLevel: 1.0, // 1.0 to 10.0
  scrollOffset: 0.0, // 0.0 to 1.0 (left edge of viewport)
  isDraggingScrub: false,
  isDraggingEvent: false,
  draggedEvent: null,
  dragStartX: 0,
  dragEventOriginalTime: 0,
  onEventsChanged: null,

  init(data, customEvents = null) {
    this.data = data;
    this.canvas = document.getElementById('timelineCanvas');
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.cursor = document.getElementById('timelineCursor');
    this.container = document.getElementById('timelineContainer');

    // 1. Initialize events from customEvents, or from scenario payload data.events, or empty list
    if (customEvents && Array.isArray(customEvents)) {
      this.events = JSON.parse(JSON.stringify(customEvents));
    } else if (data && data.events && Array.isArray(data.events)) {
      this.events = JSON.parse(JSON.stringify(data.events));
    } else {
      this.events = [];
    }

    this.bindEvents();
    this.renderTracks();
    this.updateZoomDisplay();
  },

  setTool(tool) {
    this.activeTool = tool;
    if (this.container) {
      this.container.style.cursor = tool ? 'crosshair' : 'pointer';
    }
  },

  setZoom(level, pivotRatio = 0.5) {
    const oldZoom = this.zoomLevel;
    const newZoom = Math.max(1.0, Math.min(10.0, level));

    const visibleFractionOld = 1.0 / oldZoom;
    const visibleFractionNew = 1.0 / newZoom;
    const currentCenter = this.scrollOffset + visibleFractionOld * pivotRatio;
    this.scrollOffset = Math.max(0.0, Math.min(1.0 - visibleFractionNew, currentCenter - visibleFractionNew * pivotRatio));
    this.zoomLevel = newZoom;

    this.updateZoomDisplay();
    this.renderTracks();
    if (window.AppState && this.data) {
      this.updateCursor(window.AppState.currentTick, this.data.total_ticks);
    }
  },

  zoomIn() {
    this.setZoom(this.zoomLevel * 1.4);
  },

  zoomOut() {
    this.setZoom(this.zoomLevel / 1.4);
  },

  resetZoom() {
    this.scrollOffset = 0.0;
    this.setZoom(1.0);
  },

  updateZoomDisplay() {
    const zoomValEl = document.getElementById('timelineZoomVal');
    if (zoomValEl) {
      zoomValEl.textContent = `${this.zoomLevel.toFixed(1)}x`;
    }
  },

  bindEvents() {
    if (this._eventsBound || !this.container) return;
    this._eventsBound = true;

    // Wheel Zoom & Pan
    this.container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
      const pivotRatio = mouseX / rect.width;

      if (e.ctrlKey || Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        // Vertical wheel = Zoom
        const zoomDelta = e.deltaY < 0 ? 1.25 : 0.8;
        this.setZoom(this.zoomLevel * zoomDelta, pivotRatio);
      } else {
        // Horizontal wheel = Pan
        const visibleFraction = 1.0 / this.zoomLevel;
        const panDelta = (e.deltaX / rect.width) * visibleFraction;
        this.scrollOffset = Math.max(0.0, Math.min(1.0 - visibleFraction, this.scrollOffset + panDelta));
        this.renderTracks();
        if (window.AppState && this.data) {
          this.updateCursor(window.AppState.currentTick, this.data.total_ticks);
        }
      }
    }, { passive: false });

    // ClientX to Time Helper
    const getTimeFromClientX = (clientX) => {
      if (!this.data) return 0;
      const rect = this.canvas.getBoundingClientRect();
      const screenRatio = Math.max(0, Math.min(1.0, (clientX - rect.left) / rect.width));
      const visibleFraction = 1.0 / this.zoomLevel;
      const timelineRatio = this.scrollOffset + screenRatio * visibleFraction;
      return Math.round(timelineRatio * this.data.duration_ms);
    };

    const getTickFromClientX = (clientX) => {
      if (!this.data || !this.data.ticks || this.data.ticks.length === 0) return 0;
      const rect = this.canvas.getBoundingClientRect();
      const screenRatio = Math.max(0, Math.min(1.0, (clientX - rect.left) / rect.width));
      const visibleFraction = 1.0 / this.zoomLevel;
      const timelineRatio = Math.max(0.0, Math.min(1.0, this.scrollOffset + screenRatio * visibleFraction));
      return Math.floor(timelineRatio * (this.data.ticks.length - 1));
    };

    const findEventAtPos = (clientX, clientY) => {
      if (!this.data || !this.canvas) return null;
      const rect = this.canvas.getBoundingClientRect();
      const scaleY = this.canvas.height / rect.height;
      const canvasY = (clientY - rect.top) * scaleY;

      // Event blocks are strictly rendered on Track 1 (Y: 20px to 44px)
      if (canvasY < 18 || canvasY > 44) {
        return null;
      }

      const clickTimeMs = getTimeFromClientX(clientX);

      for (const evt of this.events) {
        const durMs = evt.parameters.duration_ms || (evt.parameters.duration_s ? evt.parameters.duration_s * 1000 : 2000);
        if (clickTimeMs >= evt.sim_time_ms && clickTimeMs <= evt.sim_time_ms + durMs) {
          return evt;
        }
      }
      return null;
    };

    // Container Hover feedback
    this.container.addEventListener('mousemove', (e) => {
      if (this.isDraggingEvent || this.isDraggingScrub || this.activeTool) return;
      const isCursor = e.target && (
        e.target.id === 'timelineHandle' ||
        e.target.id === 'timelineCursor' ||
        e.target.closest('#timelineHandle') ||
        e.target.closest('#timelineCursor')
      );
      if (isCursor) {
        this.container.style.cursor = 'ew-resize';
      } else {
        const hitEvent = findEventAtPos(e.clientX, e.clientY);
        this.container.style.cursor = hitEvent ? 'grab' : 'pointer';
      }
    });

    this.container.addEventListener('mousedown', (e) => {
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;

      const isCursorClick = e.target && (
        e.target.id === 'timelineCursor' ||
        e.target.id === 'timelineHandle' ||
        e.target.closest('#timelineCursor') ||
        e.target.closest('#timelineHandle')
      );

      // 1. If active tool selected, place new event
      if (this.activeTool) {
        const newTimeMs = getTimeFromClientX(clientX);
        this.addEvent(this.activeTool, newTimeMs);
        this.setTool(null);
        document.querySelectorAll('.btn-timeline-tool').forEach(btn => btn.classList.remove('active'));
        return;
      }

      // 2. If NOT clicking the scrubber cursor/handle, check if clicked an event on Track 1
      const hitEvent = !isCursorClick ? findEventAtPos(clientX, clientY) : null;
      if (hitEvent && (e.shiftKey || e.detail === 2)) {
        if (window.openEventInspector) {
          window.openEventInspector(hitEvent);
        }
        return;
      } else if (hitEvent) {
        this.isDraggingEvent = true;
        this.draggedEvent = hitEvent;
        this.dragStartX = clientX;
        this.dragEventOriginalTime = hitEvent.sim_time_ms;
        this.container.style.cursor = 'grabbing';
        return;
      }

      // 3. Otherwise (clicking handle, ruler, or empty tracks), scrub playback
      this.isDraggingScrub = true;
      document.body.classList.add('is-scrubbing');
      const targetTick = getTickFromClientX(clientX);
      if (window.AppState) {
        window.AppState.currentTick = targetTick;
        if (window.renderTick) window.renderTick(targetTick);
      }
    });

    // Touch support for container / handle
    this.container.addEventListener('touchstart', (e) => {
      const touch = e.touches[0];
      const isCursorClick = e.target && (
        e.target.id === 'timelineCursor' ||
        e.target.id === 'timelineHandle' ||
        e.target.closest('#timelineCursor') ||
        e.target.closest('#timelineHandle')
      );
      const hitEvent = !isCursorClick ? findEventAtPos(touch.clientX, touch.clientY) : null;
      if (hitEvent) {
        this.isDraggingEvent = true;
        this.draggedEvent = hitEvent;
        this.dragStartX = touch.clientX;
        this.dragEventOriginalTime = hitEvent.sim_time_ms;
      } else {
        this.isDraggingScrub = true;
        document.body.classList.add('is-scrubbing');
        const targetTick = getTickFromClientX(touch.clientX);
        if (window.AppState) {
          window.AppState.currentTick = targetTick;
          if (window.renderTick) window.renderTick(targetTick);
        }
      }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (e.touches.length === 0) return;
      const touchX = e.touches[0].clientX;
      if (this.isDraggingEvent && this.draggedEvent && this.data) {
        const rect = this.canvas.getBoundingClientRect();
        const dx = touchX - this.dragStartX;
        const visibleFraction = 1.0 / this.zoomLevel;
        const dtMs = (dx / rect.width) * visibleFraction * this.data.duration_ms;
        const newTime = Math.max(0, Math.min(this.data.duration_ms - 500, Math.round((this.dragEventOriginalTime + dtMs) / 100) * 100));
        this.draggedEvent.sim_time_ms = newTime;
        this.renderTracks();
      } else if (this.isDraggingScrub) {
        const targetTick = getTickFromClientX(touchX);
        if (window.AppState) {
          window.AppState.currentTick = targetTick;
          if (window.renderTick) window.renderTick(targetTick);
        }
      }
    }, { passive: true });

    window.addEventListener('touchend', () => {
      if (this.isDraggingEvent) {
        this.isDraggingEvent = false;
        this.draggedEvent = null;
        if (this.onEventsChanged) {
          this.onEventsChanged(this.events);
        }
      }
      this.isDraggingScrub = false;
      document.body.classList.remove('is-scrubbing');
    });

    window.addEventListener('mousemove', (e) => {
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      if (this.isDraggingEvent && this.draggedEvent && this.data) {
        const rect = this.canvas.getBoundingClientRect();
        const dx = clientX - this.dragStartX;
        const visibleFraction = 1.0 / this.zoomLevel;
        const dtMs = (dx / rect.width) * visibleFraction * this.data.duration_ms;
        const newTime = Math.max(0, Math.min(this.data.duration_ms - 500, Math.round((this.dragEventOriginalTime + dtMs) / 100) * 100));
        this.draggedEvent.sim_time_ms = newTime;
        this.renderTracks();
      } else if (this.isDraggingScrub) {
        const targetTick = getTickFromClientX(clientX);
        if (window.AppState) {
          window.AppState.currentTick = targetTick;
          if (window.renderTick) window.renderTick(targetTick);
        }
      }
    });

    window.addEventListener('mouseup', () => {
      if (this.isDraggingEvent) {
        this.isDraggingEvent = false;
        this.draggedEvent = null;
        if (this.onEventsChanged) {
          this.onEventsChanged(this.events);
        }
      }
      this.isDraggingScrub = false;
      document.body.classList.remove('is-scrubbing');
    });

    // Double-click to inspect or add event
    this.container.addEventListener('dblclick', (e) => {
      const hitEvent = findEventAtPos(e.clientX, e.clientY);
      if (hitEvent) {
        if (window.openEventInspector) {
          window.openEventInspector(hitEvent);
        }
      } else {
        const clickTimeMs = getTimeFromClientX(e.clientX);
        this.addEvent('wind_gust', clickTimeMs);
      }
    });
  },

  addEvent(type, timeMs) {
    const idPad = String(this.events.length + 1).padStart(2, '0');
    let newEvt;

    if (type === 'wind_gust') {
      newEvt = {
        event_id: `EVT-GUST-${idPad}`,
        event_type: 'wind_gust',
        sim_time_ms: Math.max(0, timeMs),
        parameters: {
          tws_kt: 20.0,
          duration_s: 4.0,
          duration_ms: 4000,
          direction_shift_deg: 20.0,
        },
      };
    } else if (type === 'wave_impact' || type === 'slam') {
      newEvt = {
        event_id: `EVT-SLAM-${idPad}`,
        event_type: 'wave_impact',
        sim_time_ms: Math.max(0, timeMs),
        parameters: {
          impact_force_n: 15000.0,
          impact_roll_moment_nm: -28000.0,
          duration_ms: 2500,
        },
      };
    } else {
      newEvt = {
        event_id: `EVT-FAULT-${idPad}`,
        event_type: 'sensor_fault',
        sim_time_ms: Math.max(0, timeMs),
        parameters: {
          sensor: 'imu',
          duration_ms: 3000,
        },
      };
    }

    this.events.push(newEvt);
    this.renderTracks();

    if (this.onEventsChanged) {
      this.onEventsChanged(this.events);
    }
  },

  deleteEvent(eventId) {
    this.events = this.events.filter(e => e.event_id !== eventId);
    this.renderTracks();
    if (this.onEventsChanged) {
      this.onEventsChanged(this.events);
    }
  },

  updateCursor(currentTick, totalTicks) {
    if (!this.cursor || totalTicks <= 0 || !this.data) return;
    const tickRatio = currentTick / (totalTicks - 1);
    const visibleFraction = 1.0 / this.zoomLevel;
    const screenRatio = (tickRatio - this.scrollOffset) / visibleFraction;

    if (screenRatio < 0 || screenRatio > 1.0) {
      this.cursor.style.display = 'none';
    } else {
      this.cursor.style.display = 'block';
      this.cursor.style.left = `${screenRatio * 100}%`;
    }
  },

  renderTracks() {
    if (!this.canvas || !this.ctx || !this.data) return;

    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const totalTicks = this.data.ticks ? this.data.ticks.length : 0;
    if (totalTicks === 0) return;

    ctx.clearRect(0, 0, w, h);

    // Canvas Background
    ctx.fillStyle = '#040810';
    ctx.fillRect(0, 0, w, h);

    // Visible Window Calculation
    const visibleFraction = 1.0 / this.zoomLevel;
    const viewStartMs = this.scrollOffset * this.data.duration_ms;
    const viewEndMs = (this.scrollOffset + visibleFraction) * this.data.duration_ms;
    const viewDurationS = (viewEndMs - viewStartMs) / 1000;

    const timeToX = (tMs) => {
      const tRatio = tMs / this.data.duration_ms;
      const screenRatio = (tRatio - this.scrollOffset) / visibleFraction;
      return screenRatio * w;
    };

    // =========================================================================
    // 3 DISTINCT TRACK LANES BACKGROUNDS & SEPARATORS
    // =========================================================================
    // Lane 1: SCENARIO EVENTS (Y: 20 to 42, H: 22px)
    // Lane 2: SIA ADVISORY STREAM (Y: 45 to 65, H: 20px)
    // Lane 3: VESSEL ROLL & STABILITY (Y: 68 to 118, H: 50px)

    ctx.fillStyle = 'rgba(255, 255, 255, 0.015)';
    ctx.fillRect(0, 20, w, 23);

    ctx.fillStyle = 'rgba(0, 229, 255, 0.025)';
    ctx.fillRect(0, 45, w, 21);

    ctx.fillStyle = 'rgba(0, 230, 118, 0.015)';
    ctx.fillRect(0, 68, w, 52);

    // Horizontal Lane Dividers
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.07)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, 20); ctx.lineTo(w, 20);
    ctx.moveTo(0, 44); ctx.lineTo(w, 44);
    ctx.moveTo(0, 67); ctx.lineTo(w, 67);
    ctx.stroke();

    // Time Ruler Grid Vertical Lines
    let stepSec = 5;
    if (viewDurationS <= 5) stepSec = 0.5;
    else if (viewDurationS <= 10) stepSec = 1;
    else if (viewDurationS <= 20) stepSec = 2;

    const firstSec = Math.floor(viewStartMs / 1000 / stepSec) * stepSec;
    const lastSec = Math.ceil(viewEndMs / 1000 / stepSec) * stepSec;

    for (let sec = firstSec; sec <= lastSec; sec += stepSec) {
      const x = timeToX(sec * 1000);
      if (x < 0 || x > w) continue;

      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.strokeStyle = (Math.round(sec) % (stepSec * 2) === 0) ? 'rgba(51, 65, 85, 0.55)' : 'rgba(30, 41, 59, 0.35)';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = '#64748b';
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      const m = Math.floor(sec / 60).toString().padStart(2, '0');
      const s = (sec % 60).toFixed(stepSec < 1 ? 1 : 0).padStart(stepSec < 1 ? 4 : 2, '0');
      ctx.fillText(`${m}:${s}`, x + 4, 13);
    }

    // Lane Badges (Static in view or pinned)
    ctx.font = 'bold 8px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.textAlign = 'right';
    ctx.fillText('TRACK: EVENTS', w - 8, 33);
    ctx.fillStyle = 'rgba(0, 229, 255, 0.6)';
    ctx.fillText('TRACK: SIA DECISIONS', w - 8, 57);
    ctx.fillStyle = 'rgba(0, 230, 118, 0.6)';
    ctx.fillText('HEEL & STABILITY', w - 8, 80);

    // =========================================================================
    // LANE 1: CUSTOM EVENTS PLACEMENT BLOCKS
    // =========================================================================
    const trackY1 = 22;
    const trackH1 = 20;

    for (const evt of this.events) {
      const startMs = evt.sim_time_ms;
      const durMs = evt.parameters.duration_ms || (evt.parameters.duration_s ? evt.parameters.duration_s * 1000 : 2000);
      const x1 = timeToX(startMs);
      const x2 = timeToX(startMs + durMs);
      const blockW = Math.max(12, x2 - x1);

      if (x2 < 0 || x1 > w) continue;

      let fillCol = 'rgba(255, 179, 0, 0.85)';
      let borderCol = '#ffb300';
      let label = `💨 ${evt.event_id}`;

      if (evt.event_type === 'wave_impact' || evt.event_type === 'slam') {
        fillCol = 'rgba(37, 99, 235, 0.85)';
        borderCol = '#60a5fa';
        const forceKn = (evt.parameters.impact_force_n ? evt.parameters.impact_force_n / 1000 : 15).toFixed(0);
        label = `🌊 SLAM ${forceKn}kN`;
      } else if (evt.event_type === 'sensor_fault') {
        fillCol = 'rgba(239, 68, 68, 0.85)';
        borderCol = '#f87171';
        label = `⚡ FAULT: ${evt.parameters.sensor || 'IMU'}`;
      }

      ctx.fillStyle = fillCol;
      ctx.strokeStyle = borderCol;
      ctx.lineWidth = 1.5;

      // Rounded event box
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x1, trackY1, blockW, trackH1, 4);
      } else {
        ctx.rect(x1, trackY1, blockW, trackH1);
      }
      ctx.fill();
      ctx.stroke();

      // Drag handles on edges
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(x1 + 1, trackY1 + 3, 2, trackH1 - 6);
      ctx.fillRect(x1 + blockW - 3, trackY1 + 3, 2, trackH1 - 6);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px "Inter", sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x1 + 6, trackY1 + trackH1 / 2);
    }

    // =========================================================================
    // LANE 2: SIA DECISIONS STREAM (CONTINUOUS FORMATTED SPANS)
    // =========================================================================
    const trackY2 = 46;
    const trackH2 = 18;

    const startTick = Math.max(0, Math.floor((viewStartMs / this.data.duration_ms) * totalTicks));
    const endTick = Math.min(totalTicks - 1, Math.ceil((viewEndMs / this.data.duration_ms) * totalTicks));

    // Group contiguous or closely spaced decision ticks into solid ribbons
    const decisionSpans = [];
    let curSpan = null;

    for (let i = startTick; i <= endTick; i++) {
      const tick = this.data.ticks[i];
      if (!tick) continue;
      const dec = tick.sia_decision;
      const hasAction = dec && dec.selected_response !== null;

      if (hasAction) {
        if (!curSpan) {
          curSpan = {
            startMs: tick.sim_time_ms,
            endMs: tick.sim_time_ms,
            action: dec.selected_response,
            score: dec.risk_score || 0.85,
          };
        } else {
          curSpan.endMs = tick.sim_time_ms;
        }
      } else {
        if (curSpan) {
          decisionSpans.push(curSpan);
          curSpan = null;
        }
      }
    }
    if (curSpan) decisionSpans.push(curSpan);

    for (const span of decisionSpans) {
      const x1 = timeToX(span.startMs);
      const x2 = timeToX(span.endMs + 100);
      const spanW = Math.max(20, x2 - x1);

      if (x2 < 0 || x1 > w) continue;

      ctx.fillStyle = 'rgba(0, 229, 255, 0.25)';
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 1.5;

      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x1, trackY2, spanW, trackH2, 4);
      } else {
        ctx.rect(x1, trackY2, spanW, trackH2);
      }
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 9px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      const spanLabel = spanW > 60 ? `⚡ SIA: ${span.action}` : '⚡ SIA';
      ctx.fillText(spanLabel, x1 + 4, trackY2 + trackH2 / 2);
    }

    // =========================================================================
    // LANE 3: TRUE HEEL CURVE & KNOCKDOWN THRESHOLD
    // =========================================================================
    const curveBottomY = 116;
    const curveMaxHeight = 44;

    // 1. Shaded area under heel curve
    ctx.beginPath();
    let areaStarted = false;
    let firstX = 0;
    let lastX = 0;

    for (let i = startTick; i <= endTick; i++) {
      const tick = this.data.ticks[i];
      if (!tick) continue;
      const heel = Math.abs(tick.ground_truth.heel_deg);
      const x = timeToX(tick.sim_time_ms);
      const y = curveBottomY - Math.min(curveMaxHeight, (heel / 35.0) * curveMaxHeight);

      if (!areaStarted) {
        ctx.moveTo(x, curveBottomY);
        ctx.lineTo(x, y);
        areaStarted = true;
        firstX = x;
      } else {
        ctx.lineTo(x, y);
      }
      lastX = x;
    }

    if (areaStarted) {
      ctx.lineTo(lastX, curveBottomY);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, curveBottomY - curveMaxHeight, 0, curveBottomY);
      grad.addColorStop(0, 'rgba(0, 230, 118, 0.25)');
      grad.addColorStop(1, 'rgba(0, 230, 118, 0.02)');
      ctx.fillStyle = grad;
      ctx.fill();
    }

    // 2. Stroke line for heel
    ctx.beginPath();
    let lineStarted = false;
    for (let i = startTick; i <= endTick; i++) {
      const tick = this.data.ticks[i];
      if (!tick) continue;
      const heel = Math.abs(tick.ground_truth.heel_deg);
      const x = timeToX(tick.sim_time_ms);
      const y = curveBottomY - Math.min(curveMaxHeight, (heel / 35.0) * curveMaxHeight);

      if (!lineStarted) {
        ctx.moveTo(x, y);
        lineStarted = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.strokeStyle = '#00e676';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 3. Critical Knockdown Threshold Line at 25 deg
    const critY = curveBottomY - (25.0 / 35.0) * curveMaxHeight;
    ctx.beginPath();
    ctx.moveTo(0, critY);
    ctx.lineTo(w, critY);
    ctx.strokeStyle = 'rgba(255, 23, 68, 0.6)';
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = 'rgba(255, 23, 68, 0.8)';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText('25° KNOCKDOWN THRESHOLD', 6, critY - 3);
  },
};

window.TimelineRenderer = TimelineRenderer;
