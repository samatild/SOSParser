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

// Add smooth scrolling to all links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
