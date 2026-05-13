/**
 * SOSParser Advanced Log Viewer
 * Interactive log viewer with virtual scrolling, search, filters, and highlighting.
 *
 * Virtual scrolling renders only visible lines (~50 DOM elements) regardless of
 * total line count, enabling smooth display of 100K+ line log files.
 */

class LogViewer {
    // Virtual scroll constants
    static LINE_HEIGHT = 20;              // px — fixed height for monospace lines
    static BUFFER_LINES = 30;             // extra lines rendered above/below viewport
    static VIRTUAL_SCROLL_THRESHOLD = 500; // use virtual scroll when line count exceeds this

    constructor(containerId, logContent, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.originalContent = logContent || '';
        this.lines = this.originalContent.split('\n');
        // Remove trailing empty line from split
        if (this.lines.length > 0 && this.lines[this.lines.length - 1] === '') {
            this.lines.pop();
        }

        // filteredIndices: array of original line indices that pass current filters
        this.filteredIndices = this.lines.map((_, i) => i);
        this.currentMatches = [];       // indices into filteredIndices that match search
        this.currentMatchIndex = -1;
        this.searchTerm = '';
        this.useVirtualScroll = this.lines.length > LogViewer.VIRTUAL_SCROLL_THRESHOLD;
        this.scrollRAF = null;
        this._searchDebounce = null;
        this._escapeDiv = document.createElement('div');  // reusable for escapeHtml

        // Options
        this.options = {
            showLineNumbers: options.showLineNumbers !== false,
            maxHeight: options.maxHeight || '500px',
            enableRegex: options.enableRegex !== false,
            enableFilters: options.enableFilters !== false,
            ...options
        };

        // State
        this.filters = { error: false, warning: false, info: false, debug: false };
        this.searchOptions = { caseSensitive: false, regex: false, wholeWord: false };
        this.grepFilter = false;

        // Pre-compute stats once
        this._stats = null;

        this.render();
        this.attachEventListeners();
    }

    render() {
        const filterHtml = this.options.enableFilters ? `
            <div class="logviewer-filters">
                <span class="logviewer-filter-label">Filters:</span>
                <button class="logviewer-filter-btn" data-filter="error">
                    <span class="filter-indicator error"></span> ERROR
                </button>
                <button class="logviewer-filter-btn" data-filter="warning">
                    <span class="filter-indicator warning"></span> WARN
                </button>
                <button class="logviewer-filter-btn" data-filter="info">
                    <span class="filter-indicator info"></span> INFO
                </button>
                <button class="logviewer-filter-btn" data-filter="debug">
                    <span class="filter-indicator debug"></span> DEBUG
                </button>
                <button class="logviewer-btn logviewer-btn-small" data-action="clear-filters">
                    Clear Filters
                </button>
                <div class="logviewer-filter-stats"></div>
            </div>` : '';

        this.container.innerHTML = `
            <div class="logviewer">
                <!-- Toolbar -->
                <div class="logviewer-toolbar">
                    <div class="logviewer-search">
                        <input type="text"
                               class="logviewer-search-input"
                               placeholder="Search logs (supports regex)..." />
                        <div class="logviewer-search-buttons">
                            <button class="logviewer-btn logviewer-btn-small" data-action="prev-match" title="Previous Match (Shift+Enter)">↑</button>
                            <button class="logviewer-btn logviewer-btn-small" data-action="next-match" title="Next Match (Enter)">↓</button>
                            <button class="logviewer-btn logviewer-btn-small" data-action="grep-filter" title="Filter Matching Lines (like grep)">Grep</button>
                            <button class="logviewer-btn logviewer-btn-small" data-action="clear-search" title="Clear Search">✕</button>
                        </div>
                        <span class="logviewer-match-count"></span>
                    </div>
                    <div class="logviewer-options">
                        <label class="logviewer-checkbox">
                            <input type="checkbox" data-option="caseSensitive" /><span>Case Sensitive</span>
                        </label>
                        <label class="logviewer-checkbox">
                            <input type="checkbox" data-option="regex" /><span>Regex</span>
                        </label>
                        <label class="logviewer-checkbox">
                            <input type="checkbox" data-option="wholeWord" /><span>Whole Word</span>
                        </label>
                    </div>
                </div>
                ${filterHtml}
                <!-- Actions -->
                <div class="logviewer-actions">
                    <button class="logviewer-btn" data-action="copy">📋 Copy</button>
                    <button class="logviewer-btn" data-action="download">💾 Download</button>
                    <button class="logviewer-btn" data-action="wrap-toggle">↩️ Wrap Lines</button>
                </div>
                <!-- Log Content -->
                <div class="logviewer-content" style="max-height: ${this.options.maxHeight}">
                    <div class="logviewer-spacer" style="height: 0px"></div>
                    <div class="logviewer-lines"></div>
                </div>
                <!-- Status Bar -->
                <div class="logviewer-statusbar">
                    <span class="logviewer-line-count">Lines: ${this.lines.length.toLocaleString()}</span>
                    <span class="logviewer-visible-count"></span>
                </div>
            </div>
        `;

        this.contentEl = this.container.querySelector('.logviewer-content');
        this.linesEl = this.container.querySelector('.logviewer-lines');
        this.spacerEl = this.container.querySelector('.logviewer-spacer');

        this.updateLogDisplay();
    }

    attachEventListeners() {
        const container = this.container;

        // Search input — debounced for large files
        const searchInput = container.querySelector('.logviewer-search-input');
        searchInput.addEventListener('input', () => {
            clearTimeout(this._searchDebounce);
            this._searchDebounce = setTimeout(() => this.handleSearch(), 150);
        });
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.navigateMatches(e.shiftKey ? 'prev' : 'next');
            }
        });

        // Action buttons
        container.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => this.handleAction(btn.dataset.action));
        });

        // Filter buttons
        container.querySelectorAll('[data-filter]').forEach(btn => {
            btn.addEventListener('click', () => this.toggleFilter(btn.dataset.filter));
        });

        // Search options
        container.querySelectorAll('[data-option]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.searchOptions[checkbox.dataset.option] = checkbox.checked;
                this.handleSearch();
            });
        });

        // Virtual scroll listener
        this.contentEl.addEventListener('scroll', () => {
            if (!this.useVirtualScroll) return;
            if (this.scrollRAF) return;
            this.scrollRAF = requestAnimationFrame(() => {
                this.renderVisibleLines();
                this.scrollRAF = null;
            });
        });
    }

    // ──────────────────── Display ────────────────────

    updateLogDisplay() {
        // Recompute filtered indices
        this.filteredIndices = [];
        const hasActiveFilter = Object.values(this.filters).some(f => f);

        for (let i = 0; i < this.lines.length; i++) {
            const line = this.lines[i];

            // Grep filter: only show lines matching search term
            if (this.grepFilter && this.searchTerm) {
                if (!this.lineMatchesSearch(line, this.searchTerm)) continue;
            }

            // Level filters
            if (hasActiveFilter) {
                const passes =
                    (this.filters.error   && this.isLogLevel(line, 'error'))   ||
                    (this.filters.warning && this.isLogLevel(line, 'warning')) ||
                    (this.filters.info    && this.isLogLevel(line, 'info'))    ||
                    (this.filters.debug   && this.isLogLevel(line, 'debug'));
                if (!passes) continue;
            }

            this.filteredIndices.push(i);
        }

        if (this.useVirtualScroll) {
            // Set spacer height to represent the full list for scrollbar
            this.spacerEl.style.height = (this.filteredIndices.length * LogViewer.LINE_HEIGHT) + 'px';
            this.renderVisibleLines();
        } else {
            this.spacerEl.style.height = '0px';
            this.renderAllLines();
        }

        this.updateStats();
    }

    renderVisibleLines() {
        const scrollTop = this.contentEl.scrollTop;
        const viewportHeight = this.contentEl.clientHeight;

        const startIdx = Math.max(0,
            Math.floor(scrollTop / LogViewer.LINE_HEIGHT) - LogViewer.BUFFER_LINES);
        const endIdx = Math.min(this.filteredIndices.length,
            Math.ceil((scrollTop + viewportHeight) / LogViewer.LINE_HEIGHT) + LogViewer.BUFFER_LINES);

        // Position the rendered chunk at the correct offset (absolute over spacer)
        this.linesEl.style.position = 'absolute';
        this.linesEl.style.left = '0';
        this.linesEl.style.right = '0';
        this.linesEl.style.top = (startIdx * LogViewer.LINE_HEIGHT) + 'px';

        let html = '';
        for (let i = startIdx; i < endIdx; i++) {
            html += this.buildLineHtml(i);
        }
        this.linesEl.innerHTML = html || '<div class="logviewer-empty">No lines match the current filters</div>';
    }

    renderAllLines() {
        let html = '';
        for (let i = 0; i < this.filteredIndices.length; i++) {
            html += this.buildLineHtml(i);
        }
        this.linesEl.style.position = '';
        this.linesEl.style.left = '';
        this.linesEl.style.right = '';
        this.linesEl.style.top = '';
        this.linesEl.innerHTML = html || '<div class="logviewer-empty">No lines match the current filters</div>';
    }

    buildLineHtml(filteredIdx) {
        const origIdx = this.filteredIndices[filteredIdx];
        const line = this.lines[origIdx];
        const lineNumber = origIdx + 1;
        const displayLine = this.searchTerm
            ? this.highlightMatches(line, this.searchTerm)
            : this.escapeHtml(line);
        const logLevelClass = this.getLogLevelClass(line);
        const isCurrent = this.currentMatchIndex >= 0 &&
                          this.currentMatches[this.currentMatchIndex] === filteredIdx;
        const heightStyle = this.useVirtualScroll
            ? ` style="height:${LogViewer.LINE_HEIGHT}px;box-sizing:border-box"`
            : '';

        return `<div class="logviewer-line ${logLevelClass}${isCurrent ? ' logviewer-current-match' : ''}" data-line="${lineNumber}"${heightStyle}>${this.options.showLineNumbers ? `<span class="logviewer-line-number">${lineNumber}</span>` : ''}<span class="logviewer-line-content">${displayLine}</span></div>`;
    }

    // ──────────────────── Search ────────────────────

    handleSearch() {
        this.searchTerm = this.container.querySelector('.logviewer-search-input').value;

        if (!this.searchTerm) {
            this.currentMatches = [];
            this.currentMatchIndex = -1;
            this.updateLogDisplay();
            this.updateMatchCount();
            return;
        }

        // If grep filter is on, recompute filtered indices
        if (this.grepFilter) {
            this.updateLogDisplay();
        }

        // Find all matches within filtered lines
        this.currentMatches = [];
        for (let i = 0; i < this.filteredIndices.length; i++) {
            const origIdx = this.filteredIndices[i];
            if (this.lineMatchesSearch(this.lines[origIdx], this.searchTerm)) {
                this.currentMatches.push(i); // index into filteredIndices
            }
        }

        this.currentMatchIndex = this.currentMatches.length > 0 ? 0 : -1;

        // Re-render for highlights
        if (this.useVirtualScroll) {
            this.renderVisibleLines();
        } else {
            this.renderAllLines();
        }

        this.updateMatchCount();

        if (this.currentMatchIndex >= 0) {
            this.scrollToMatch(this.currentMatchIndex);
        }
    }

    lineMatchesSearch(line, term) {
        try {
            if (this.searchOptions.regex) {
                const flags = this.searchOptions.caseSensitive ? 'g' : 'gi';
                return new RegExp(term, flags).test(line);
            }
            if (this.searchOptions.wholeWord) {
                const flags = this.searchOptions.caseSensitive ? 'g' : 'gi';
                return new RegExp(`\\b${this.escapeRegex(term)}\\b`, flags).test(line);
            }
            const a = this.searchOptions.caseSensitive ? line : line.toLowerCase();
            const b = this.searchOptions.caseSensitive ? term : term.toLowerCase();
            return a.includes(b);
        } catch (e) {
            return false;
        }
    }

    highlightMatches(line, term) {
        if (!term) return this.escapeHtml(line);
        try {
            let pattern;
            if (this.searchOptions.regex) {
                pattern = term;
            } else {
                const escaped = this.escapeRegex(term);
                pattern = this.searchOptions.wholeWord ? `\\b${escaped}\\b` : escaped;
            }
            const flags = this.searchOptions.caseSensitive ? 'g' : 'gi';
            const regex = new RegExp(`(${pattern})`, flags);
            return this.escapeHtml(line).replace(regex, '<mark class="logviewer-highlight">$1</mark>');
        } catch (e) {
            return this.escapeHtml(line);
        }
    }

    navigateMatches(direction) {
        if (this.currentMatches.length === 0) return;
        if (direction === 'next') {
            this.currentMatchIndex = (this.currentMatchIndex + 1) % this.currentMatches.length;
        } else {
            this.currentMatchIndex = this.currentMatchIndex <= 0
                ? this.currentMatches.length - 1
                : this.currentMatchIndex - 1;
        }
        this.scrollToMatch(this.currentMatchIndex);
        this.updateMatchCount();
    }

    scrollToMatch(matchIndex) {
        if (matchIndex < 0 || matchIndex >= this.currentMatches.length) return;
        const filteredIdx = this.currentMatches[matchIndex];

        if (this.useVirtualScroll) {
            // Scroll so the matched line is centered in the viewport
            const targetTop = filteredIdx * LogViewer.LINE_HEIGHT - this.contentEl.clientHeight / 2;
            this.contentEl.scrollTop = Math.max(0, targetTop);
            // Re-render to apply current-match styling
            this.currentMatchIndex = matchIndex;
            requestAnimationFrame(() => this.renderVisibleLines());
        } else {
            const lineElements = this.linesEl.querySelectorAll('.logviewer-line');
            if (lineElements[filteredIdx]) {
                lineElements[filteredIdx].scrollIntoView({ behavior: 'smooth', block: 'center' });
                lineElements.forEach(el => el.classList.remove('logviewer-current-match'));
                lineElements[filteredIdx].classList.add('logviewer-current-match');
            }
        }
    }

    updateMatchCount() {
        const el = this.container.querySelector('.logviewer-match-count');
        if (this.currentMatches.length > 0) {
            el.textContent = `${this.currentMatchIndex + 1} of ${this.currentMatches.length.toLocaleString()}`;
        } else {
            el.textContent = this.searchTerm ? 'No matches' : '';
        }
    }

    // ──────────────────── Filters ────────────────────

    toggleFilter(filterName) {
        this.filters[filterName] = !this.filters[filterName];
        const btn = this.container.querySelector(`[data-filter="${filterName}"]`);
        btn.classList.toggle('active', this.filters[filterName]);
        this._stats = null; // invalidate cache
        this.updateLogDisplay();
    }

    isLogLevel(line, level) {
        switch (level) {
            case 'error':   return /\b(error|err|fatal|critical|crit)\b/i.test(line);
            case 'warning': return /\b(warn|warning|caution)\b/i.test(line);
            case 'info':    return /\b(info|information|notice)\b/i.test(line);
            case 'debug':   return /\b(debug|trace|verbose)\b/i.test(line);
            default:        return false;
        }
    }

    getLogLevelClass(line) {
        if (this.isLogLevel(line, 'error'))   return 'log-error';
        if (this.isLogLevel(line, 'warning')) return 'log-warning';
        if (this.isLogLevel(line, 'info'))    return 'log-info';
        if (this.isLogLevel(line, 'debug'))   return 'log-debug';
        return '';
    }

    // ──────────────────── Actions ────────────────────

    handleAction(action) {
        switch (action) {
            case 'prev-match':    this.navigateMatches('prev'); break;
            case 'next-match':    this.navigateMatches('next'); break;
            case 'clear-search':
                this.container.querySelector('.logviewer-search-input').value = '';
                this.grepFilter = false;
                this.updateGrepButtonState();
                this.handleSearch();
                break;
            case 'grep-filter':   this.toggleGrepFilter(); break;
            case 'clear-filters':
                Object.keys(this.filters).forEach(k => this.filters[k] = false);
                this.container.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
                this._stats = null;
                this.updateLogDisplay();
                break;
            case 'copy':          this.copyToClipboard(); break;
            case 'download':      this.downloadLogs(); break;
            case 'wrap-toggle':   this.toggleWrap(); break;
        }
    }

    copyToClipboard() {
        const text = this.filteredIndices.map(i => this.lines[i]).join('\n');
        const btn = this.container.querySelector('[data-action="copy"]');
        const orig = btn.textContent;

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => { btn.textContent = '✓ Copied!'; setTimeout(() => btn.textContent = orig, 2000); })
                .catch(() => this._fallbackCopy(text, btn, orig));
        } else {
            this._fallbackCopy(text, btn, orig);
        }
    }

    _fallbackCopy(text, btn, orig) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try {
            const ok = document.execCommand('copy');
            btn.textContent = ok ? '✓ Copied!' : '✗ Copy failed';
        } catch { btn.textContent = '✗ Copy failed'; }
        setTimeout(() => btn.textContent = orig, 2000);
        document.body.removeChild(ta);
    }

    downloadLogs() {
        const text = this.filteredIndices.map(i => this.lines[i]).join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sosparser-logs-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }

    toggleWrap() {
        const content = this.contentEl;
        content.classList.toggle('nowrap');
        const btn = this.container.querySelector('[data-action="wrap-toggle"]');
        btn.textContent = content.classList.contains('nowrap') ? '↩️ Unwrap Lines' : '↩️ Wrap Lines';
    }

    toggleGrepFilter() {
        const searchInput = this.container.querySelector('.logviewer-search-input');
        if (!searchInput.value) {
            const btn = this.container.querySelector('[data-action="grep-filter"]');
            const t = btn.title;
            btn.title = 'Enter a search term first';
            setTimeout(() => btn.title = t, 2000);
            return;
        }
        this.grepFilter = !this.grepFilter;
        this.updateGrepButtonState();
        this.updateLogDisplay();
    }

    updateGrepButtonState() {
        const btn = this.container.querySelector('[data-action="grep-filter"]');
        if (btn) {
            btn.classList.toggle('active', this.grepFilter);
            btn.style.backgroundColor = this.grepFilter ? '#4CAF50' : '';
            btn.style.color = this.grepFilter ? 'white' : '';
        }
    }

    // ──────────────────── Stats ────────────────────

    updateStats() {
        const visibleEl = this.container.querySelector('.logviewer-visible-count');
        if (visibleEl) {
            if (this.filteredIndices.length !== this.lines.length) {
                visibleEl.textContent = `Showing: ${this.filteredIndices.length.toLocaleString()} of ${this.lines.length.toLocaleString()}`;
            } else {
                visibleEl.textContent = '';
            }
        }

        const statsEl = this.container.querySelector('.logviewer-filter-stats');
        if (statsEl && this.options.enableFilters) {
            if (!this._stats) {
                let errorCount = 0, warnCount = 0, infoCount = 0, debugCount = 0;
                for (let i = 0; i < this.lines.length; i++) {
                    const l = this.lines[i];
                    if (this.isLogLevel(l, 'error'))   errorCount++;
                    if (this.isLogLevel(l, 'warning')) warnCount++;
                    if (this.isLogLevel(l, 'info'))    infoCount++;
                    if (this.isLogLevel(l, 'debug'))   debugCount++;
                }
                this._stats = { errorCount, warnCount, infoCount, debugCount };
            }
            const s = this._stats;
            statsEl.innerHTML = `
                <span class="stat-error">${s.errorCount.toLocaleString()} errors</span>
                <span class="stat-warning">${s.warnCount.toLocaleString()} warnings</span>
                <span class="stat-info">${s.infoCount.toLocaleString()} info</span>
                <span class="stat-debug">${s.debugCount.toLocaleString()} debug</span>
            `;
        }
    }

    // ──────────────────── Utilities ────────────────────

    escapeHtml(text) {
        this._escapeDiv.textContent = text;
        return this._escapeDiv.innerHTML;
    }

    escapeRegex(text) {
        return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}

// Make LogViewer available globally
window.LogViewer = LogViewer;
