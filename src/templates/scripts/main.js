// SOSParser Report - Interactive JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            this.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
    
    // Subtab switching
    const subtabButtons = document.querySelectorAll('.subtab-button');
    
    subtabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetSubtab = this.getAttribute('data-subtab');
            
            // Get parent tab content to scope subtab changes
            const parentTab = this.closest('.tab-content');
            if (!parentTab) return;
            
            // Remove active class from all subtab buttons and contents in this tab
            const siblingButtons = parentTab.querySelectorAll('.subtab-button');
            const siblingContents = parentTab.querySelectorAll('.subtab-content');
            
            siblingButtons.forEach(btn => btn.classList.remove('active'));
            siblingContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked subtab and corresponding content
            this.classList.add('active');
            const targetContent = parentTab.querySelector(`#${targetSubtab}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
            
        });
    });
    
    // Process tree toggle functionality
    const processToggles = document.querySelectorAll('.process-toggle');
    processToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const targetId = this.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);
            const icon = this.querySelector('.toggle-icon');
            
            if (targetElement) {
                if (targetElement.classList.contains('expanded')) {
                    targetElement.classList.remove('expanded');
                    targetElement.classList.add('collapsed');
                    icon.textContent = '▶';
                } else {
                    targetElement.classList.remove('collapsed');
                    targetElement.classList.add('expanded');
                    icon.textContent = '▼';
                }
            }
        });
    });
    
    // Expand/Collapse all buttons for process tree
    const expandAllBtn = document.getElementById('expand-all-processes');
    const collapseAllBtn = document.getElementById('collapse-all-processes');
    
    if (expandAllBtn) {
        expandAllBtn.addEventListener('click', function() {
            const processTree = document.querySelector('.process-tree-container');
            if (processTree) {
                const children = processTree.querySelectorAll('.process-children');
                const icons = processTree.querySelectorAll('.toggle-icon');
                children.forEach(child => {
                    child.classList.remove('collapsed');
                    child.classList.add('expanded');
                });
                icons.forEach(icon => {
                    icon.textContent = '▼';
                });
            }
        });
    }
    
    if (collapseAllBtn) {
        collapseAllBtn.addEventListener('click', function() {
            const processTree = document.querySelector('.process-tree-container');
            if (processTree) {
                const children = processTree.querySelectorAll('.process-children');
                const icons = processTree.querySelectorAll('.toggle-icon');
                children.forEach(child => {
                    child.classList.remove('expanded');
                    child.classList.add('collapsed');
                });
                icons.forEach(icon => {
                    icon.textContent = '▶';
                });
            }
        });
    }


    // Health summary finding rows:
    // - If the row has evidence, clicking the whole row toggles the evidence panel.
    // - If no evidence but has a tab target, clicking navigates to that tab.
    document.querySelectorAll('.health-finding').forEach(function(row) {
        row.addEventListener('click', function(e) {
            e.preventDefault();
            var wrapper = this.closest('.health-finding-wrapper');
            var panel = wrapper ? wrapper.querySelector('.health-evidence') : null;
            if (panel) {
                // Toggle evidence panel and rotate chevron
                panel.classList.toggle('expanded');
                var chevron = this.querySelector('.health-evidence-chevron');
                if (chevron) chevron.classList.toggle('open');
            } else {
                // No evidence – navigate to linked tab
                var target = this.getAttribute('data-tab-target');
                if (!target) return;
                var tabBtn = document.querySelector('.tab-button[data-tab="' + target + '"]');
                if (tabBtn) tabBtn.click();
            }
        });
    });
});

// Toggle scenario details
function toggleScenarioDetails(header) {
    const details = header.nextElementSibling;
    const button = header.querySelector('.toggle-details');
    
    if (details.classList.contains('active')) {
        details.classList.remove('active');
        button.textContent = 'Show Details';
    } else {
        details.classList.add('active');
        button.textContent = 'Hide Details';
    }
}

// Add smooth scrolling to all anchor links (skip health-finding links handled above)
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    if (anchor.classList.contains('health-finding')) return;
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const href = this.getAttribute('href');
        if (!href || href === '#') return;
        const target = document.querySelector(href);
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ─── Report Search Overlay ───────────────────────────────────────────────────
(function () {
    var overlay     = document.getElementById('report-search-overlay');
    var input       = document.getElementById('report-search-input');
    var countEl     = document.getElementById('report-search-count');
    var prevBtn     = document.getElementById('report-search-prev');
    var nextBtn     = document.getElementById('report-search-next');
    var closeBtn    = document.getElementById('report-search-close');
    var resultsList = document.getElementById('report-search-results');

    if (!overlay) return;   // guard: only runs inside a rendered report

    var MAX_LIST = 200;     // max result items shown in the panel
    var marks    = [];      // all <mark> elements in page order
    var current  = -1;

    // ── helpers ────────────────────────────────────────────────────────────

    function escHtml(s) {
        return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    // Return "Tab → Subtab" label for an element using the button text in the DOM.
    function getLocation(el) {
        var parts = [];
        var tab    = el.closest('.tab-content');
        var subtab = el.closest('.subtab-content');
        if (tab) {
            var tabBtn = document.querySelector('.tab-button[data-tab="' + tab.id + '"]');
            if (tabBtn) parts.push(tabBtn.textContent.trim());
        }
        if (subtab) {
            var stBtn = document.querySelector('.subtab-button[data-subtab="' + subtab.id + '"]');
            if (stBtn) parts.push(stBtn.textContent.trim());
        }
        return parts.join(' → ') || 'Report';
    }

    // Build a short ±45-char snippet of plain text around a match inside `fullText`.
    function makeSnippet(fullText, matchStart, matchLen) {
        var CTX   = 45;
        var start = Math.max(0, matchStart - CTX);
        var end   = Math.min(fullText.length, matchStart + matchLen + CTX);
        var pre   = (start > 0 ? '\u2026' : '') + escHtml(fullText.slice(start, matchStart));
        var hit   = '<mark>' + escHtml(fullText.slice(matchStart, matchStart + matchLen)) + '</mark>';
        var post  = escHtml(fullText.slice(matchStart + matchLen, end)) + (end < fullText.length ? '\u2026' : '');
        return pre + hit + post;
    }

    // ── DOM walking ────────────────────────────────────────────────────────

    function collectTextNodes() {
        var nodes = [];
        document.querySelectorAll('h2, h3, h4, h5, th, td, pre, code').forEach(function (el) {
            walkText(el, nodes);
        });
        return nodes;
    }

    function walkText(node, out) {
        if (node.nodeType === Node.TEXT_NODE) {
            if (node.textContent.trim()) out.push(node);
        } else if (node.nodeType === Node.ELEMENT_NODE && node.nodeName !== 'MARK') {
            node.childNodes.forEach(function (c) { walkText(c, out); });
        }
    }

    // ── mark management ────────────────────────────────────────────────────

    function clearMarks() {
        document.querySelectorAll('mark.search-hit').forEach(function (m) {
            var p = m.parentNode;
            p.replaceChild(document.createTextNode(m.textContent), m);
            p.normalize();
        });
    }

    // ── core search ────────────────────────────────────────────────────────

    function doSearch(term) {
        clearMarks();
        marks   = [];
        current = -1;
        resultsList.innerHTML = '';

        if (!term || term.length < 2) {
            countEl.textContent = 'Type to search';
            resultsList.innerHTML = '<div class="sri-empty">Type at least 2 characters</div>';
            return;
        }

        var lower     = term.toLowerCase();
        var textNodes = collectTextNodes();

        // snippets[i] stores the HTML snippet for marks[i] (built before DOM replacement)
        var snippets = [];

        textNodes.forEach(function (node) {
            var text       = node.textContent;
            var lowerText  = text.toLowerCase();
            var idx        = lowerText.indexOf(lower);
            if (idx === -1) return;

            var frag = document.createDocumentFragment();
            var pos  = 0;
            while (idx !== -1) {
                if (idx > pos) frag.appendChild(document.createTextNode(text.slice(pos, idx)));
                var mark       = document.createElement('mark');
                mark.className = 'search-hit';
                mark.textContent = text.slice(idx, idx + term.length);
                frag.appendChild(mark);
                marks.push(mark);
                snippets.push(makeSnippet(text, idx, term.length));
                pos = idx + term.length;
                idx = lowerText.indexOf(lower, pos);
            }
            if (pos < text.length) frag.appendChild(document.createTextNode(text.slice(pos)));
            node.parentNode.replaceChild(frag, node);
        });

        if (marks.length === 0) {
            countEl.textContent = 'No matches';
            resultsList.innerHTML = '<div class="sri-empty">No matches found</div>';
            return;
        }

        buildResultsList(snippets);
        navigateTo(0);
    }

    // ── results list ───────────────────────────────────────────────────────

    function buildResultsList(snippets) {
        resultsList.innerHTML = '';
        var shown = Math.min(marks.length, MAX_LIST);
        for (var i = 0; i < shown; i++) {
            (function (idx) {
                var item  = document.createElement('div');
                item.className    = 'search-result-item';
                item.dataset.idx  = idx;
                var loc   = getLocation(marks[idx]);
                item.innerHTML =
                    '<span class="sri-loc">' + escHtml(loc) + '</span>' +
                    '<span class="sri-snippet">' + snippets[idx] + '</span>';
                item.addEventListener('click', function () { navigateTo(idx); });
                resultsList.appendChild(item);
            }(i));
        }
        if (marks.length > MAX_LIST) {
            var more = document.createElement('div');
            more.className   = 'sri-more';
            more.textContent = '\u2026 and ' + (marks.length - MAX_LIST) + ' more matches not shown';
            resultsList.appendChild(more);
        }
    }

    function syncResultsList(idx) {
        var items = resultsList.querySelectorAll('.search-result-item');
        items.forEach(function (item) { item.classList.remove('active'); });
        if (idx < items.length) {
            items[idx].classList.add('active');
            items[idx].scrollIntoView({ block: 'nearest' });
        }
    }

    // ── navigation ─────────────────────────────────────────────────────────

    function navigateTo(idx) {
        if (marks.length === 0) return;
        if (current >= 0) marks[current].classList.remove('current');
        current = (idx + marks.length) % marks.length;
        marks[current].classList.add('current');
        var n = marks.length;
        countEl.textContent = (current + 1) + ' / ' + n + ' match' + (n !== 1 ? 'es' : '');
        activateContaining(marks[current]);
        marks[current].scrollIntoView({ behavior: 'smooth', block: 'center' });
        syncResultsList(current);
    }

    function activateContaining(el) {
        // ---- subtab first ----
        var subtabContent = el.closest('.subtab-content');
        if (subtabContent && !subtabContent.classList.contains('active')) {
            var subtabId  = subtabContent.id;
            var parentTab = subtabContent.closest('.tab-content');
            if (parentTab) {
                parentTab.querySelectorAll('.subtab-button').forEach(function (b) { b.classList.remove('active'); });
                parentTab.querySelectorAll('.subtab-content').forEach(function (c) { c.classList.remove('active'); });
                subtabContent.classList.add('active');
                var stBtn = parentTab.querySelector('.subtab-button[data-subtab="' + subtabId + '"]');
                if (stBtn) stBtn.classList.add('active');
            }
        }
        // ---- then main tab ----
        var tabContent = el.closest('.tab-content');
        if (tabContent && !tabContent.classList.contains('active')) {
            var tabId = tabContent.id;
            document.querySelectorAll('.tab-button').forEach(function (b) { b.classList.remove('active'); });
            document.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
            tabContent.classList.add('active');
            var tabBtn = document.querySelector('.tab-button[data-tab="' + tabId + '"]');
            if (tabBtn) tabBtn.classList.add('active');
        }
    }

    // ── open / close ───────────────────────────────────────────────────────

    function openOverlay() {
        overlay.classList.add('active');
        input.focus();
        input.select();
    }

    function closeOverlay() {
        overlay.classList.remove('active');
        clearMarks();
        input.value = '';
        countEl.textContent = 'Type to search';
        resultsList.innerHTML = '';
        marks   = [];
        current = -1;
    }

    // ── event wiring ───────────────────────────────────────────────────────

    document.addEventListener('keydown', function (e) {
        if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            e.preventDefault(); openOverlay(); return;
        }
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
            e.preventDefault(); openOverlay(); return;
        }
        if (!overlay.classList.contains('active')) return;
        if (e.key === 'Escape') {
            closeOverlay();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            e.shiftKey ? navigateTo(current - 1) : navigateTo(current + 1);
        } else if (e.key === 'ArrowDown') {
            e.preventDefault(); navigateTo(current + 1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault(); navigateTo(current - 1);
        }
    });

    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) closeOverlay();
    });

    closeBtn.addEventListener('click', closeOverlay);
    prevBtn.addEventListener('click',  function () { navigateTo(current - 1); });
    nextBtn.addEventListener('click',  function () { navigateTo(current + 1); });

    var debounceTimer;
    input.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () { doSearch(input.value); }, 220);
    });
}());
