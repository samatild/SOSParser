/**
 * SOSParser Advanced Log Viewer
 * Interactive log viewer with search, filters, and highlighting
 */

class LogViewer {
    constructor(containerId, logContent, options = {}) {
        this.container = document.getElementById(containerId);
        this.originalContent = logContent || '';
        this.lines = this.originalContent.split('\n');
        this.filteredLines = [...this.lines];
        this.currentMatches = [];
        this.currentMatchIndex = -1;
        
        // Options
        this.options = {
            showLineNumbers: options.showLineNumbers !== false,
            maxHeight: options.maxHeight || '500px',
            enableRegex: options.enableRegex !== false,
            enableFilters: options.enableFilters !== false,
            ...options
        };
        
        // State
        this.filters = {
            error: false,
            warning: false,
            info: false,
            debug: false
        };
        
        this.searchOptions = {
            caseSensitive: false,
            regex: false,
            wholeWord: false
        };
        
        this.grepFilter = false;
        
        this.render();
        this.attachEventListeners();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="logviewer">
                <!-- Toolbar -->
                <div class="logviewer-toolbar">
                    <!-- Search Section -->
                    <div class="logviewer-search">
                        <input type="text" 
                               class="logviewer-search-input" 
                               placeholder="Search logs (supports regex)..." />
                        <div class="logviewer-search-buttons">
                            <button class="logviewer-btn logviewer-btn-small" data-action="prev-match" title="Previous Match (Shift+Enter)">
                                ↑
                            </button>
                            <button class="logviewer-btn logviewer-btn-small" data-action="next-match" title="Next Match (Enter)">
                                ↓
                            </button>
                            <button class="logviewer-btn logviewer-btn-small" data-action="grep-filter" title="Filter Matching Lines (like grep)">
                                Grep
                            </button>
                            <button class="logviewer-btn logviewer-btn-small" data-action="clear-search" title="Clear Search">
                                ✕
                            </button>
                        </div>
                        <span class="logviewer-match-count"></span>
                    </div>
                    
                    <!-- Search Options -->
                    <div class="logviewer-options">
                        <label class="logviewer-checkbox">
                            <input type="checkbox" data-option="caseSensitive" />
                            <span>Case Sensitive</span>
                        </label>
                        <label class="logviewer-checkbox">
                            <input type="checkbox" data-option="regex" />
                            <span>Regex</span>
                        </label>
                        <label class="logviewer-checkbox">
                            <input type="checkbox" data-option="wholeWord" />
                            <span>Whole Word</span>
                        </label>
                    </div>
                </div>
                
                <!-- Filters -->
                ${this.options.enableFilters ? `
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
                </div>
                ` : ''}
                
                <!-- Actions -->
                <div class="logviewer-actions">
                    <button class="logviewer-btn" data-action="copy">📋 Copy</button>
                    <button class="logviewer-btn" data-action="download">💾 Download</button>
                    <button class="logviewer-btn" data-action="wrap-toggle">↩️ Wrap Lines</button>
                </div>
                
                <!-- Log Content -->
                <div class="logviewer-content" style="max-height: ${this.options.maxHeight}">
                    <div class="logviewer-lines"></div>
                </div>
                
                <!-- Status Bar -->
                <div class="logviewer-statusbar">
                    <span class="logviewer-line-count">Lines: ${this.lines.length}</span>
                    <span class="logviewer-visible-count"></span>
                </div>
            </div>
        `;
        
        this.updateLogDisplay();
    }
    
    attachEventListeners() {
        const container = this.container;
        
        // Search input
        const searchInput = container.querySelector('.logviewer-search-input');
        searchInput.addEventListener('input', () => this.handleSearch());
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    this.navigateMatches('prev');
                } else {
                    this.navigateMatches('next');
                }
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
    }
    
    updateLogDisplay() {
        const linesContainer = this.container.querySelector('.logviewer-lines');
        const searchInput = this.container.querySelector('.logviewer-search-input');
        const searchTerm = searchInput ? searchInput.value : '';
        
        // Apply filters
        this.filteredLines = this.lines.filter((line, index) => {
            // Apply grep filter first if active
            if (this.grepFilter && searchTerm) {
                if (!this.lineMatchesSearch(line, searchTerm)) {
                    return false;
                }
            }
            
            // Check if any log level filter is active
            const hasActiveFilter = Object.values(this.filters).some(f => f);
            if (!hasActiveFilter) return true;
            
            const lineLower = line.toLowerCase();
            if (this.filters.error && this.isLogLevel(line, 'error')) return true;
            if (this.filters.warning && this.isLogLevel(line, 'warning')) return true;
            if (this.filters.info && this.isLogLevel(line, 'info')) return true;
            if (this.filters.debug && this.isLogLevel(line, 'debug')) return true;
            
            return false;
        });
        
        // Render lines
        let html = '';
        this.filteredLines.forEach((line, index) => {
            const originalIndex = this.lines.indexOf(line);
            const lineNumber = originalIndex + 1;
            const highlightedLine = searchTerm ? this.highlightMatches(line, searchTerm) : this.escapeHtml(line);
            const logLevelClass = this.getLogLevelClass(line);
            
            html += `
                <div class="logviewer-line ${logLevelClass}" data-line="${lineNumber}">
                    ${this.options.showLineNumbers ? `<span class="logviewer-line-number">${lineNumber}</span>` : ''}
                    <span class="logviewer-line-content">${highlightedLine}</span>
                </div>
            `;
        });
        
        linesContainer.innerHTML = html || '<div class="logviewer-empty">No lines match the current filters</div>';
        
        // Update stats
        this.updateStats();
    }
    
    handleSearch() {
        const searchInput = this.container.querySelector('.logviewer-search-input');
        const searchTerm = searchInput.value;
        
        if (!searchTerm) {
            this.currentMatches = [];
            this.currentMatchIndex = -1;
            this.updateLogDisplay();
            this.updateMatchCount();
            return;
        }
        
        // Find all matches
        this.currentMatches = [];
        this.filteredLines.forEach((line, index) => {
            if (this.lineMatchesSearch(line, searchTerm)) {
                this.currentMatches.push(index);
            }
        });
        
        this.currentMatchIndex = this.currentMatches.length > 0 ? 0 : -1;
        this.updateLogDisplay();
        this.updateMatchCount();
        
        if (this.currentMatchIndex >= 0) {
            this.scrollToMatch(this.currentMatchIndex);
        }
    }
    
    lineMatchesSearch(line, searchTerm) {
        try {
            if (this.searchOptions.regex) {
                const flags = this.searchOptions.caseSensitive ? 'g' : 'gi';
                const regex = new RegExp(searchTerm, flags);
                return regex.test(line);
            } else {
                const lineCmp = this.searchOptions.caseSensitive ? line : line.toLowerCase();
                const termCmp = this.searchOptions.caseSensitive ? searchTerm : searchTerm.toLowerCase();
                
                if (this.searchOptions.wholeWord) {
                    const regex = new RegExp(`\\b${this.escapeRegex(termCmp)}\\b`, this.searchOptions.caseSensitive ? 'g' : 'gi');
                    return regex.test(line);
                } else {
                    return lineCmp.includes(termCmp);
                }
            }
        } catch (e) {
            return false;
        }
    }
    
    highlightMatches(line, searchTerm) {
        if (!searchTerm) return this.escapeHtml(line);
        
        try {
            let regex;
            if (this.searchOptions.regex) {
                const flags = this.searchOptions.caseSensitive ? 'gi' : 'gi';
                regex = new RegExp(`(${searchTerm})`, flags);
            } else {
                const escaped = this.escapeRegex(searchTerm);
                const pattern = this.searchOptions.wholeWord ? `\\b${escaped}\\b` : escaped;
                const flags = this.searchOptions.caseSensitive ? 'gi' : 'gi';
                regex = new RegExp(`(${pattern})`, flags);
            }
            
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
        
        const lineIndex = this.currentMatches[matchIndex];
        const linesContainer = this.container.querySelector('.logviewer-lines');
        const lineElements = linesContainer.querySelectorAll('.logviewer-line');
        
        if (lineElements[lineIndex]) {
            lineElements[lineIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Highlight current match
            lineElements.forEach(el => el.classList.remove('logviewer-current-match'));
            lineElements[lineIndex].classList.add('logviewer-current-match');
        }
    }
    
    updateMatchCount() {
        const matchCount = this.container.querySelector('.logviewer-match-count');
        if (this.currentMatches.length > 0) {
            matchCount.textContent = `${this.currentMatchIndex + 1} of ${this.currentMatches.length}`;
        } else {
            matchCount.textContent = this.container.querySelector('.logviewer-search-input').value ? 'No matches' : '';
        }
    }
    
    toggleFilter(filterName) {
        this.filters[filterName] = !this.filters[filterName];
        
        // Update button state
        const btn = this.container.querySelector(`[data-filter="${filterName}"]`);
        btn.classList.toggle('active', this.filters[filterName]);
        
        this.updateLogDisplay();
    }
    
    handleAction(action) {
        switch (action) {
            case 'prev-match':
                this.navigateMatches('prev');
                break;
            case 'next-match':
                this.navigateMatches('next');
                break;
            case 'clear-search':
                this.container.querySelector('.logviewer-search-input').value = '';
                this.grepFilter = false;
                this.updateGrepButtonState();
                this.handleSearch();
                break;
            case 'grep-filter':
                this.toggleGrepFilter();
                break;
            case 'clear-filters':
                Object.keys(this.filters).forEach(key => this.filters[key] = false);
                this.container.querySelectorAll('[data-filter]').forEach(btn => btn.classList.remove('active'));
                this.updateLogDisplay();
                break;
            case 'copy':
                this.copyToClipboard();
                break;
            case 'download':
                this.downloadLogs();
                break;
            case 'wrap-toggle':
                this.toggleWrap();
                break;
        }
    }
    
    copyToClipboard() {
        const text = this.filteredLines.join('\n');
        const btn = this.container.querySelector('[data-action="copy"]');
        const originalText = btn.textContent;
        
        // Try modern clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    btn.textContent = '✓ Copied!';
                    setTimeout(() => btn.textContent = originalText, 2000);
                })
                .catch(err => {
                    console.error('Clipboard API failed:', err);
                    this.fallbackCopyToClipboard(text, btn, originalText);
                });
        } else {
            // Fallback for older browsers
            this.fallbackCopyToClipboard(text, btn, originalText);
        }
    }
    
    fallbackCopyToClipboard(text, btn, originalText) {
        // Create a temporary textarea element
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                btn.textContent = '✓ Copied!';
                setTimeout(() => btn.textContent = originalText, 2000);
            } else {
                btn.textContent = '✗ Copy failed';
                setTimeout(() => btn.textContent = originalText, 2000);
            }
        } catch (err) {
            console.error('Fallback copy failed:', err);
            btn.textContent = '✗ Copy failed';
            setTimeout(() => btn.textContent = originalText, 2000);
        } finally {
            document.body.removeChild(textarea);
        }
    }
    
    downloadLogs() {
        const text = this.filteredLines.join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sosparser-logs-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    toggleWrap() {
        const content = this.container.querySelector('.logviewer-content');
        content.classList.toggle('nowrap');
        const btn = this.container.querySelector('[data-action="wrap-toggle"]');
        btn.textContent = content.classList.contains('nowrap') ? '↩️ Unwrap Lines' : '↩️ Wrap Lines';
    }
    
    updateStats() {
        const visibleCount = this.container.querySelector('.logviewer-visible-count');
        const filterStats = this.container.querySelector('.logviewer-filter-stats');
        
        if (visibleCount) {
            const hasFilters = Object.values(this.filters).some(f => f);
            if (hasFilters || this.filteredLines.length !== this.lines.length) {
                visibleCount.textContent = `Showing: ${this.filteredLines.length} of ${this.lines.length}`;
            } else {
                visibleCount.textContent = '';
            }
        }
        
        if (filterStats && this.options.enableFilters) {
            const errorCount = this.lines.filter(l => this.isLogLevel(l, 'error')).length;
            const warnCount = this.lines.filter(l => this.isLogLevel(l, 'warning')).length;
            const infoCount = this.lines.filter(l => this.isLogLevel(l, 'info')).length;
            const debugCount = this.lines.filter(l => this.isLogLevel(l, 'debug')).length;
            
            filterStats.innerHTML = `
                <span class="stat-error">${errorCount} errors</span>
                <span class="stat-warning">${warnCount} warnings</span>
                <span class="stat-info">${infoCount} info</span>
                <span class="stat-debug">${debugCount} debug</span>
            `;
        }
    }
    
    isLogLevel(line, level) {
        const lineLower = line.toLowerCase();
        switch (level) {
            case 'error':
                return /\b(error|err|fatal|critical|crit)\b/i.test(line);
            case 'warning':
                return /\b(warn|warning|caution)\b/i.test(line);
            case 'info':
                return /\b(info|information|notice)\b/i.test(line);
            case 'debug':
                return /\b(debug|trace|verbose)\b/i.test(line);
            default:
                return false;
        }
    }
    
    getLogLevelClass(line) {
        if (this.isLogLevel(line, 'error')) return 'log-error';
        if (this.isLogLevel(line, 'warning')) return 'log-warning';
        if (this.isLogLevel(line, 'info')) return 'log-info';
        if (this.isLogLevel(line, 'debug')) return 'log-debug';
        return '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    escapeRegex(text) {
        return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    toggleGrepFilter() {
        const searchInput = this.container.querySelector('.logviewer-search-input');
        const searchTerm = searchInput.value;
        
        if (!searchTerm) {
            // Can't activate grep filter without a search term
            const btn = this.container.querySelector('[data-action="grep-filter"]');
            const originalTitle = btn.title;
            btn.title = 'Enter a search term first';
            setTimeout(() => btn.title = originalTitle, 2000);
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
}

// Make LogViewer available globally
window.LogViewer = LogViewer;
