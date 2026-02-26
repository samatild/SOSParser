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
