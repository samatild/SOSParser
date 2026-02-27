/**
 * SOSParser Web Application
 * Main JavaScript for upload interface, chunked uploads, and version checking
 */

// ========== Chunked Upload System ==========
const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
let currentUpload = null;

// Format bytes for display
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Format time remaining
function formatETA(seconds) {
  if (!seconds || seconds === Infinity || seconds < 0) return 'Calculating...';
  if (seconds < 60) return `${Math.ceil(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.ceil(seconds % 60)}s`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

// ========== Console Functions ==========
let consoleExpanded = false;

function toggleConsole(forceState) {
  const panel = document.getElementById('console-panel');
  const toggle = document.getElementById('console-toggle');
  const icon = toggle.querySelector('.console-toggle-icon');
  const text = toggle.querySelector('.console-toggle-text');
  
  consoleExpanded = forceState !== undefined ? forceState : !consoleExpanded;
  
  if (consoleExpanded) {
    panel.classList.add('expanded');
    icon.textContent = '▼';
    text.textContent = 'Hide Console Output';
  } else {
    panel.classList.remove('expanded');
    icon.textContent = '▶';
    text.textContent = 'Show Console Output';
  }
}

function clearConsole() {
  document.getElementById('console-output').innerHTML = '';
}

function addConsoleLine(message, type = 'default') {
  const output = document.getElementById('console-output');
  const line = document.createElement('div');
  line.className = `console-line console-${type}`;
  line.textContent = message;
  output.appendChild(line);
  // Auto-scroll to bottom
  output.scrollTop = output.scrollHeight;
}

// Chunked uploader class
class ChunkedUploader {
  constructor(file) {
    this.file = file;
    this.uploadId = null;
    this.totalChunks = 0;
    this.uploadedChunks = 0;
    this.uploadedBytes = 0;
    this.startTime = null;
    this.cancelled = false;
    this.speedSamples = [];
    this.lastSampleTime = 0;
    this.lastSampleBytes = 0;
  }

  updateProgress() {
    const percentage = Math.round((this.uploadedBytes / this.file.size) * 100);
    const now = Date.now();
    
    // Calculate speed (sample every 500ms)
    if (now - this.lastSampleTime >= 500) {
      const bytesDelta = this.uploadedBytes - this.lastSampleBytes;
      const timeDelta = (now - this.lastSampleTime) / 1000;
      const speed = bytesDelta / timeDelta;
      
      this.speedSamples.push(speed);
      if (this.speedSamples.length > 10) this.speedSamples.shift();
      
      this.lastSampleTime = now;
      this.lastSampleBytes = this.uploadedBytes;
    }
    
    // Average speed from samples
    const avgSpeed = this.speedSamples.length > 0 
      ? this.speedSamples.reduce((a, b) => a + b, 0) / this.speedSamples.length 
      : 0;
    
    // Calculate ETA
    const remainingBytes = this.file.size - this.uploadedBytes;
    const eta = avgSpeed > 0 ? remainingBytes / avgSpeed : Infinity;

    // Update UI
    document.getElementById('upload-progress-fill').style.width = `${percentage}%`;
    document.getElementById('upload-percentage').textContent = `${percentage}%`;
    document.getElementById('upload-speed').textContent = avgSpeed > 0 ? `${formatBytes(avgSpeed)}/s` : '';
    document.getElementById('upload-bytes').textContent = `${formatBytes(this.uploadedBytes)} / ${formatBytes(this.file.size)}`;
    document.getElementById('upload-eta').textContent = formatETA(eta);
    document.getElementById('upload-status').textContent = 'Uploading...';
  }

  async init() {
    const response = await fetch('/api/upload/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: this.file.name,
        fileSize: this.file.size,
        chunkSize: CHUNK_SIZE,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to initialize upload');
    }

    const data = await response.json();
    this.uploadId = data.uploadId;
    this.totalChunks = data.totalChunks;
    return data;
  }

  async uploadChunk(chunkIndex) {
    if (this.cancelled) throw new Error('Upload cancelled');

    const start = chunkIndex * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, this.file.size);
    const chunk = this.file.slice(start, end);

    const formData = new FormData();
    formData.append('uploadId', this.uploadId);
    formData.append('chunkIndex', chunkIndex);
    formData.append('chunk', chunk);

    const response = await fetch('/api/upload/chunk', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Failed to upload chunk ${chunkIndex}`);
    }

    this.uploadedChunks++;
    this.uploadedBytes = Math.min(end, this.file.size);
    this.updateProgress();

    return response.json();
  }

  async complete() {
    document.getElementById('upload-status').textContent = 'Starting analysis...';
    document.getElementById('upload-title').textContent = 'Analyzing Report';
    document.getElementById('upload-progress-fill').classList.add('analyzing');

    // Read SAR checkbox from the form
    const analyzeSar = true; // Always probe for SAR files; user selects days in the next step

    // Show and expand console for analysis phase
    document.getElementById('console-container').style.display = 'block';
    toggleConsole(true);
    clearConsole();
    addConsoleLine('Finalizing upload...', 'info');

    const response = await fetch('/api/upload/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uploadId: this.uploadId, analyzeSar }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to complete upload');
    }

    const result = await response.json();

    // SAR selection step: let user pick which days to analyze
    if (result.status === 'sar_selection' && result.token) {
      return await this.showSarSelector(result.token, result.sarFiles || []);
    }

    if (result.status === 'processing' && result.token) {
      // Connect to SSE log stream
      addConsoleLine('Connecting to analysis stream...', 'info');
      return await this.streamLogs(result.token);
    }

    return result;
  }

  async showSarSelector(token, sarFiles) {
    // Update status text; leave progress bar as-is (upload 100%)
    document.getElementById('upload-status').textContent = 'Select SAR days to analyze:';
    document.getElementById('console-container').style.display = 'none';

    const selector = document.getElementById('sar-selector');
    selector.style.display = 'block';

    // Populate the file list with checkboxes
    const list = document.getElementById('sar-file-list');
    list.innerHTML = '';
    sarFiles.forEach(function(f) {
      const label = document.createElement('label');
      label.className = 'sar-file-item';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = f.name;
      cb.checked = true;
      const nameSpan = document.createElement('span');
      nameSpan.className = 'sar-file-name';
      nameSpan.textContent = f.name;
      const dateSpan = document.createElement('span');
      dateSpan.className = 'sar-file-date';
      dateSpan.textContent = f.date_display;
      label.appendChild(cb);
      label.appendChild(nameSpan);
      label.appendChild(dateSpan);
      list.appendChild(label);
    });

    // Select All / Deselect All buttons
    document.getElementById('sar-select-all').onclick = function() {
      list.querySelectorAll('input[type=checkbox]').forEach(function(cb) { cb.checked = true; });
    };
    document.getElementById('sar-select-none').onclick = function() {
      list.querySelectorAll('input[type=checkbox]').forEach(function(cb) { cb.checked = false; });
    };

    // Return a Promise resolved when the user clicks "Start Analysis"
    return new Promise((resolve, reject) => {
      document.getElementById('sar-start-btn').onclick = async () => {
        const selectedFiles = Array.from(
          list.querySelectorAll('input[type=checkbox]:checked')
        ).map(cb => cb.value);

        // Hide SAR selector, show console
        selector.style.display = 'none';
        const progressContainer = document.getElementById('upload-progress-container');
        if (progressContainer) progressContainer.style.display = '';
        document.getElementById('console-container').style.display = 'block';
        toggleConsole(true);
        clearConsole();
        document.getElementById('upload-status').textContent = 'Starting analysis...';
        addConsoleLine(`Starting analysis with ${selectedFiles.length} SAR file(s)...`, 'info');

        try {
          const r = await fetch('/api/upload/start-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, selectedSarFiles: selectedFiles }),
          });
          const data = await r.json();
          if (!r.ok) throw new Error(data.error || 'Failed to start analysis');
          addConsoleLine('Connecting to analysis stream...', 'info');
          const result = await this.streamLogs(token);
          resolve(result);
        } catch (err) {
          reject(err);
        }
      };
    });
  }

  async streamLogs(token) {
    return new Promise((resolve, reject) => {
      const eventSource = new EventSource(`/api/analysis/${token}/logs`);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'log') {
            addConsoleLine(data.message);
            document.getElementById('upload-status').textContent = 'Analyzing...';
          } else if (data.type === 'complete') {
            eventSource.close();
            addConsoleLine('Analysis complete! Redirecting...', 'success');
            resolve({ redirectUrl: data.redirectUrl });
          } else if (data.type === 'error') {
            eventSource.close();
            addConsoleLine(`Error: ${data.error}`, 'error');
            reject(new Error(data.error));
          }
          // Ignore heartbeat messages
        } catch (e) {
          console.warn('Failed to parse SSE message:', e);
        }
      };
      
      eventSource.onerror = (err) => {
        eventSource.close();
        addConsoleLine('Connection to analysis stream lost', 'error');
        // Try polling for status instead
        this.pollStatus(token).then(resolve).catch(reject);
      };
    });
  }
  
  async pollStatus(token) {
    addConsoleLine('Polling for analysis status...', 'info');
    while (true) {
      try {
        const response = await fetch(`/api/analysis/${token}/status`);
        const data = await response.json();
        
        if (data.status === 'complete') {
          addConsoleLine('Analysis complete!', 'success');
          return { redirectUrl: data.redirectUrl };
        } else if (data.status === 'error') {
          throw new Error(data.error || 'Analysis failed');
        }
      } catch (e) {
        if (e.message !== 'Analysis failed') {
          console.warn('Status poll error:', e);
        } else {
          throw e;
        }
      }
      await new Promise(r => setTimeout(r, 2000));
    }
  }

  async cancel() {
    this.cancelled = true;
    if (this.uploadId) {
      try {
        await fetch(`/api/upload/${this.uploadId}`, { method: 'DELETE' });
      } catch (e) {
        console.warn('Failed to cancel upload on server:', e);
      }
    }
  }

  async start() {
    this.startTime = Date.now();
    this.lastSampleTime = Date.now();
    this.lastSampleBytes = 0;

    // Initialize upload session
    await this.init();

    // Upload chunks sequentially (could be parallelized for better speed)
    for (let i = 0; i < this.totalChunks; i++) {
      if (this.cancelled) throw new Error('Upload cancelled');
      await this.uploadChunk(i);
    }

    // Complete and analyze
    return await this.complete();
  }
}

// ========== Version Checker ==========
async function checkVersion() {
  const versionStatus = document.getElementById('version-status');
  
  try {
    const response = await fetch('/api/version/check');
    const data = await response.json();
    
    if (data.status === 'ok') {
      if (data.update_available) {
        versionStatus.innerHTML = `<a href="https://github.com/samatild/SOSParser/blob/main/README.md#update" target="_blank" class="version-outdated" title="Current: v${data.current}, Latest: v${data.latest}">⚠️ Update available: v${data.latest}</a>`;
      } else {
        versionStatus.innerHTML = `<span class="version-current">✓ Up to date</span>`;
        versionStatus.title = `Current version: v${data.current}`;
      }
    } else if (data.latest === null) {
      versionStatus.innerHTML = `<span class="version-unknown">• Version check unavailable</span>`;
      versionStatus.title = 'Unable to check for updates';
    } else {
      versionStatus.innerHTML = `<span class="version-current">✓ Up to date</span>`;
    }
  } catch (error) {
    versionStatus.innerHTML = `<span class="version-unknown">• Version check unavailable</span>`;
    versionStatus.title = 'Unable to check for updates';
  }
}

// ========== Report Browser (only in non-public mode) ==========
function initReportBrowser() {
  const browseBtn = document.getElementById('browse-reports-btn');
  if (!browseBtn) return;

  const browser = document.getElementById('report-browser');
  const backdrop = document.getElementById('browser-backdrop');
  const closeBtn = document.getElementById('close-browser-btn');
  const reportList = document.getElementById('report-list');

  function closeBrowser() {
    browser.classList.remove('active');
    backdrop.style.display = 'none';
  }

  function openBrowser() {
    browser.classList.add('active');
    backdrop.style.display = 'block';
    loadReports();
  }

  async function loadReports() {
    reportList.innerHTML = '<p class="browser-loading">Loading...</p>';
    try {
      const res = await fetch('/api/reports');
      if (!res.ok) throw new Error('Failed to load reports');
      const data = await res.json();
      renderReports(data.items || []);
    } catch (err) {
      reportList.innerHTML = '<p class="browser-error">Failed to load reports.</p>';
    }
  }

  function renderReports(items) {
    if (!items.length) {
      reportList.innerHTML = '<p class="browser-empty">No reports found.</p>';
      return;
    }
    const frag = document.createDocumentFragment();
    items.forEach((item) => {
      const name = (item.path || 'report.html').split('/')[0] || 'report';
      const row = document.createElement('div');
      row.className = 'report-row';

      const info = document.createElement('div');
      info.className = 'report-info';
      const title = document.createElement('div');
      title.className = 'report-token';
      title.textContent = name;
      const meta = document.createElement('div');
      meta.className = 'report-meta';
      const ts = item.modified ? new Date(item.modified).toLocaleString() : '';
      const size = item.size ? ` · ${Math.max(1, Math.round(item.size / 1024))} KB` : '';
      meta.textContent = `${item.path || 'report.html'}${ts ? ' · ' + ts : ''}${size}`;
      info.appendChild(title);
      info.appendChild(meta);

      const actions = document.createElement('div');
      actions.className = 'report-actions';

      const openBtn = document.createElement('a');
      openBtn.className = 'btn-link';
      openBtn.href = item.url || `/view/${encodeURIComponent(item.token)}?path=${encodeURIComponent(item.path || 'report.html')}`;
      openBtn.textContent = 'Open';
      actions.appendChild(openBtn);

      const delBtn = document.createElement('button');
      delBtn.className = 'btn-link danger';
      delBtn.textContent = 'Delete';
      delBtn.addEventListener('click', async () => {
        if (!confirm('Delete this report?')) return;
        try {
          const res = await fetch(`/api/reports/${encodeURIComponent(item.token)}`, { method: 'DELETE' });
          if (!res.ok) throw new Error();
          loadReports();
        } catch (err) {
          alert('Failed to delete report.');
        }
      });
      actions.appendChild(delBtn);

      row.appendChild(info);
      row.appendChild(actions);
      frag.appendChild(row);
    });
    reportList.innerHTML = '';
    reportList.appendChild(frag);
  }

  browseBtn.addEventListener('click', openBrowser);
  closeBtn.addEventListener('click', closeBrowser);
  backdrop.addEventListener('click', closeBrowser);
}

// ========== Initialize on DOM Ready ==========
document.addEventListener('DOMContentLoaded', function() {
  // Console event handlers
  const consoleToggle = document.getElementById('console-toggle');
  const consoleClear = document.getElementById('console-clear');
  
  if (consoleToggle) {
    consoleToggle.addEventListener('click', () => toggleConsole());
  }
  
  if (consoleClear) {
    consoleClear.addEventListener('click', clearConsole);
  }

  // Handle form submission
  const analyzeForm = document.getElementById('analyze-form');
  if (analyzeForm) {
    analyzeForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const fileInput = document.getElementById('sosreport_file');
      const file = fileInput.files[0];
      
      if (!file) {
        alert('Please select a file first.');
        return;
      }

      // Show upload overlay
      const overlay = document.getElementById('upload-overlay');
      overlay.style.display = 'flex';
      
      // Reset UI state
      document.getElementById('upload-title').textContent = 'Uploading File';
      document.getElementById('upload-progress-fill').style.width = '0%';
      document.getElementById('upload-progress-fill').classList.remove('analyzing');
      document.getElementById('upload-percentage').textContent = '0%';
      document.getElementById('upload-speed').textContent = '';
      document.getElementById('upload-bytes').textContent = `0 B / ${formatBytes(file.size)}`;
      document.getElementById('upload-eta').textContent = 'Calculating...';
      document.getElementById('upload-status').textContent = 'Initializing upload...';
      document.getElementById('cancel-upload-btn').style.display = 'block';
      
      // Reset console (hidden during upload, shown during analysis)
      document.getElementById('console-container').style.display = 'none';
      clearConsole();
      toggleConsole(false);

      currentUpload = new ChunkedUploader(file);

      try {
        const result = await currentUpload.start();
        
        if (result.redirectUrl) {
          window.location.href = result.redirectUrl;
        }
      } catch (err) {
        overlay.style.display = 'none';
        if (err.message !== 'Upload cancelled') {
          alert('Upload failed: ' + err.message);
        }
      } finally {
        currentUpload = null;
      }
    });
  }

  // Cancel upload button
  const cancelBtn = document.getElementById('cancel-upload-btn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', async function() {
      if (currentUpload) {
        await currentUpload.cancel();
        document.getElementById('upload-overlay').style.display = 'none';
      }
    });
  }

  // Update file input display
  const fileInput = document.getElementById('sosreport_file');
  if (fileInput) {
    fileInput.addEventListener('change', function(e) {
      const display = document.querySelector('.file-text');
      if (e.target.files.length > 0) {
        const file = e.target.files[0];
        display.textContent = `${file.name} (${formatBytes(file.size)})`;
      } else {
        display.textContent = 'Select file...';
      }
    });
  }

  // Initialize report browser
  initReportBrowser();

  // Check version on page load
  if (document.getElementById('version-checker')) {
    checkVersion();
  }
});
