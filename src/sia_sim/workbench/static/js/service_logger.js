/**
 * SIA Simulation Workbench — Service Diagnostics Logger Module
 *
 * Captures, filters, displays, and exports structured simulation events:
 * - [SIA_CORE]  : Active sensing inquiries, rule activations, candidate evaluations, decisions
 * - [PHYSICS]   : Aerodynamic transitions, reefing power changes, heel/roll thresholds
 * - [SKIPPER]   : Wardrobe selections, reef confirmations, manual interventions
 * - [ORACLE]    : Safety envelope checks, latency evaluations, verdict status
 * - [SIM_RUNNER]: Clock ticks, auto-pauses, playback state changes
 */

class ServiceLogger {
  constructor() {
    this.logs = [];
    this.maxLogs = 500;
    this.activeFilter = 'ALL';
    this.autoScroll = true;
    this.searchQuery = '';
    this.isExpanded = false;
  }

  init() {
    this.feedEl = document.getElementById('serviceLogFeed');
    this.countEl = document.getElementById('serviceLogCount');
    this.filterChips = document.querySelectorAll('.btn-log-filter');
    this.autoScrollCheckbox = document.getElementById('chkLogAutoScroll');
    this.searchInput = document.getElementById('inputLogSearch');
    this.btnClear = document.getElementById('btnLogClear');
    this.btnExportJson = document.getElementById('btnLogExportJson');
    this.btnExportCsv = document.getElementById('btnLogExportCsv');
    this.btnToggleDrawer = document.getElementById('btnLogToggleDrawer');
    this.zoneLogs = document.getElementById('zoneServiceLogs');

    if (this.filterChips) {
      this.filterChips.forEach(chip => {
        chip.addEventListener('click', () => {
          this.filterChips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          this.activeFilter = chip.getAttribute('data-filter') || 'ALL';
          this.render();
        });
      });
    }

    if (this.autoScrollCheckbox) {
      this.autoScrollCheckbox.addEventListener('change', (e) => {
        this.autoScroll = e.target.checked;
      });
    }

    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.render();
      });
    }

    if (this.btnClear) {
      this.btnClear.addEventListener('click', () => {
        this.clear();
      });
    }

    if (this.btnExportJson) {
      this.btnExportJson.addEventListener('click', () => {
        this.exportJSON();
      });
    }

    if (this.btnExportCsv) {
      this.btnExportCsv.addEventListener('click', () => {
        this.exportCSV();
      });
    }

    if (this.btnToggleDrawer) {
      this.btnToggleDrawer.addEventListener('click', () => {
        this.toggleDrawer();
      });
    }

    // Initial system boot log
    this.log('SIM_RUNNER', 'INFO', 'SIA Diagnostics Service Logger initialized and ready.', { version: '2.2.0' }, 0);
  }

  log(subsystem, level, message, details = null, simTimeMs = null) {
    const timeMs = simTimeMs !== null ? simTimeMs : (window.AppState ? (window.AppState.currentSimTimeMs || 0) : 0);
    const entry = {
      id: Date.now() + '-' + Math.random().toString(36).substr(2, 6),
      timestamp: new Date().toISOString(),
      simTimeMs: Math.round(timeMs),
      simTimeFormatted: this.formatSimTime(timeMs),
      subsystem: subsystem.toUpperCase(),
      level: level.toUpperCase(),
      message: String(message),
      details: details ? (typeof details === 'object' ? JSON.parse(JSON.stringify(details)) : details) : null,
    };

    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    this.render();
  }

  formatSimTime(ms) {
    const totalSecs = Math.max(0, ms / 1000);
    const mins = Math.floor(totalSecs / 60).toString().padStart(2, '0');
    const secs = (totalSecs % 60).toFixed(2).padStart(5, '0');
    return `${mins}:${secs}`;
  }

  toggleDrawer() {
    this.isExpanded = !this.isExpanded;
    if (this.zoneLogs) {
      this.zoneLogs.classList.toggle('expanded', this.isExpanded);
    }
    if (this.btnToggleDrawer) {
      this.btnToggleDrawer.textContent = this.isExpanded ? '▼ Свернуть логи' : '▲ Развернуть логи';
    }
  }

  clear() {
    this.logs = [];
    this.render();
  }

  render() {
    if (!this.feedEl) return;

    const filtered = this.logs.filter(entry => {
      if (this.activeFilter !== 'ALL' && entry.subsystem !== this.activeFilter) {
        return false;
      }
      if (this.searchQuery) {
        const text = `${entry.simTimeFormatted} ${entry.subsystem} ${entry.level} ${entry.message} ${JSON.stringify(entry.details || '')}`.toLowerCase();
        if (!text.includes(this.searchQuery)) {
          return false;
        }
      }
      return true;
    });

    if (this.countEl) {
      this.countEl.textContent = `${filtered.length} / ${this.logs.length} events`;
    }

    this.feedEl.innerHTML = '';
    if (filtered.length === 0) {
      const emptyRow = document.createElement('div');
      emptyRow.className = 'log-row log-empty';
      emptyRow.textContent = 'Нет записей в журнале по текущему фильтру...';
      this.feedEl.appendChild(emptyRow);
      return;
    }

    const fragment = document.createDocumentFragment();
    filtered.forEach(entry => {
      const row = document.createElement('div');
      row.className = `log-row log-level-${entry.level.toLowerCase()} log-subsys-${entry.subsystem.toLowerCase()}`;

      let detailsHtml = '';
      if (entry.details) {
        const detailsStr = typeof entry.details === 'object' ? JSON.stringify(entry.details) : String(entry.details);
        detailsHtml = `<span class="log-details" title="${this.escapeHtml(detailsStr)}">${this.escapeHtml(detailsStr)}</span>`;
      }

      row.innerHTML = `
        <span class="log-time">[${entry.simTimeFormatted}]</span>
        <span class="log-badge log-badge-${entry.subsystem.toLowerCase()}">${entry.subsystem}</span>
        <span class="log-level">${entry.level}</span>
        <span class="log-msg">${this.escapeHtml(entry.message)}</span>
        ${detailsHtml}
      `;

      fragment.appendChild(row);
    });

    this.feedEl.appendChild(fragment);

    if (this.autoScroll) {
      this.feedEl.scrollTop = this.feedEl.scrollHeight;
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  exportJSON() {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(this.logs, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', dataStr);
    dlAnchor.setAttribute('download', `sia_simulation_logs_${Date.now()}.json`);
    dlAnchor.click();
  }

  exportCSV() {
    if (this.logs.length === 0) return;
    const headers = ['simTimeFormatted', 'simTimeMs', 'subsystem', 'level', 'message', 'details', 'timestamp'];
    const csvRows = [headers.join(',')];

    this.logs.forEach(row => {
      const values = headers.map(h => {
        let v = row[h];
        if (typeof v === 'object' && v !== null) {
          v = JSON.stringify(v);
        }
        const escaped = ('' + (v || '')).replace(/"/g, '""');
        return `"${escaped}"`;
      });
      csvRows.push(values.join(','));
    });

    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sia_simulation_logs_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}

// Singleton instantiation
window.ServiceLogger = new ServiceLogger();
window.Logger = window.ServiceLogger;

document.addEventListener('DOMContentLoaded', () => {
  window.ServiceLogger.init();
});
