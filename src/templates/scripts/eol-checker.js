// End-of-Life Checker for OS Distributions
// Fetches support status from endoflife.date API (client-side)

(function() {
    'use strict';

    // Map OS IDs from os-release to endoflife.date product names
    const OS_ID_MAP = {
        // Red Hat family
        'rhel': 'rhel',
        'centos': 'centos',
        'rocky': 'rocky-linux',
        'almalinux': 'almalinux',
        'fedora': 'fedora',
        'oracle': 'oracle-linux',
        'ol': 'oracle-linux',  // Oracle Linux may use 'ol' as ID
        
        // Debian family
        'debian': 'debian',
        'ubuntu': 'ubuntu',
        'raspbian': 'debian',
        
        // SUSE family
        'sles': 'sles',
        'sled': 'sles',
        'opensuse': 'opensuse',
        'opensuse-leap': 'opensuse',
        'opensuse-tumbleweed': 'opensuse',
        
        // Others
        'amzn': 'amazon-linux',
        'amazon': 'amazon-linux',
        'arch': 'arch-linux',
        'alpine': 'alpine',
    };

    // Normalize version string for comparison
    function normalizeVersion(version) {
        if (!version) return '';
        // Remove common suffixes and clean up
        return version.replace(/['"]/g, '').trim().split(/[-_]/)[0];
    }

    // Compare version strings (simplified semantic versioning)
    function versionMatch(osVersion, releaseVersion) {
        const osNorm = normalizeVersion(osVersion);
        const relNorm = normalizeVersion(releaseVersion);
        
        // Handle exact match
        if (osNorm === relNorm) return true;
        
        // Handle major version match (e.g., "8.10" matches "8")
        const osParts = osNorm.split('.');
        const relParts = relNorm.split('.');
        
        // Check if major version matches
        if (osParts[0] === relParts[0]) {
            // If release only specifies major, it's a match
            if (relParts.length === 1) return true;
            // If both have minor, check minor version too
            if (osParts.length >= 2 && relParts.length >= 2) {
                return osParts[1] === relParts[1];
            }
            return true;
        }
        
        return false;
    }

    // Find matching release from API response
    function findMatchingRelease(releases, versionId) {
        if (!releases || !Array.isArray(releases)) return null;
        
        for (const release of releases) {
            // Check name field (primary version identifier)
            if (versionMatch(versionId, release.name)) {
                return release;
            }
        }
        return null;
    }

    // Determine support status from release data
    function determineStatus(release) {
        if (!release) {
            return {
                status: 'unknown',
                label: 'Unknown',
                cssClass: 'eol-unknown',
                details: 'Version not found in support database'
            };
        }

        const now = new Date();
        
        // Check if EOL
        if (release.isEol) {
            // Check if in Extended Security Maintenance
            if (release.isEoes === false && release.eoesFrom) {
                const eoesDate = new Date(release.eoesFrom);
                if (now < eoesDate) {
                    return {
                        status: 'esm',
                        label: 'Extended Support Available',
                        cssClass: 'eol-esm',
                        details: `Standard support ended. Extended Security Maintenance available until ${release.eoesFrom}`
                    };
                }
            }
            return {
                status: 'eol',
                label: 'End of Life',
                cssClass: 'eol-unsupported',
                details: `Support ended on ${release.eolFrom || 'unknown date'}`
            };
        }

        // Check if still maintained
        if (release.isMaintained) {
            let details = 'Actively supported';
            if (release.eolFrom) {
                details += ` until ${release.eolFrom}`;
            }
            if (release.isLts) {
                return {
                    status: 'lts',
                    label: 'LTS - Supported',
                    cssClass: 'eol-supported-lts',
                    details: details + ' (Long Term Support)'
                };
            }
            return {
                status: 'supported',
                label: 'Supported',
                cssClass: 'eol-supported',
                details: details
            };
        }

        // Default to unknown if we can't determine
        return {
            status: 'unknown',
            label: 'Status Unknown',
            cssClass: 'eol-unknown',
            details: 'Could not determine support status'
        };
    }

    // Create the status badge element (as link if URL provided)
    function createStatusBadge(statusInfo, releasePolicyUrl) {
        const badge = document.createElement(releasePolicyUrl ? 'a' : 'span');
        badge.className = `eol-badge ${statusInfo.cssClass}`;
        badge.textContent = statusInfo.label;
        badge.title = statusInfo.details + (releasePolicyUrl ? ' (click for release policy)' : '');
        
        if (releasePolicyUrl) {
            badge.href = releasePolicyUrl;
            badge.target = '_blank';
            badge.rel = 'noopener noreferrer';
        }
        
        return badge;
    }

    // Create loading indicator
    function createLoadingIndicator() {
        const loading = document.createElement('span');
        loading.className = 'eol-badge eol-loading';
        loading.textContent = 'Checking support status...';
        loading.id = 'eol-status-badge';
        return loading;
    }

    // Create error badge
    function createErrorBadge(message) {
        const badge = document.createElement('span');
        badge.className = 'eol-badge eol-error';
        badge.textContent = 'Support Status Unavailable';
        badge.title = message || 'Failed to check support status';
        return badge;
    }

    // Fetch EOL data from endoflife.date API
    async function fetchEolData(productName) {
        const url = `https://endoflife.date/api/v1/products/${productName}/`;
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    return { error: 'Product not found', notFound: true };
                }
                return { error: `API error: ${response.status}` };
            }
            
            const data = await response.json();
            return { data: data };
        } catch (error) {
            return { error: error.message || 'Network error' };
        }
    }

    // Main function to check EOL status
    async function checkEolStatus() {
        // Get OS info from the page
        const osInfoElement = document.getElementById('os-eol-data');
        if (!osInfoElement) {
            console.log('EOL Checker: No OS data element found');
            return;
        }

        const osId = osInfoElement.dataset.osId;
        const versionId = osInfoElement.dataset.versionId;
        
        if (!osId) {
            console.log('EOL Checker: No OS ID available');
            return;
        }

        // Find target element for the badge
        const targetElement = document.getElementById('eol-status-container');
        if (!targetElement) {
            console.log('EOL Checker: No target container found');
            return;
        }

        // Show loading state
        targetElement.innerHTML = '';
        targetElement.appendChild(createLoadingIndicator());

        // Map OS ID to endoflife.date product name
        const productName = OS_ID_MAP[osId.toLowerCase()];
        if (!productName) {
            targetElement.innerHTML = '';
            const badge = createStatusBadge({
                status: 'unknown',
                label: 'Unknown Distribution',
                cssClass: 'eol-unknown',
                details: `Distribution "${osId}" not in support database`
            });
            badge.id = 'eol-status-badge';
            targetElement.appendChild(badge);
            return;
        }

        // Fetch EOL data
        const result = await fetchEolData(productName);
        
        targetElement.innerHTML = '';
        
        if (result.error) {
            const badge = createErrorBadge(result.error);
            badge.id = 'eol-status-badge';
            targetElement.appendChild(badge);
            return;
        }

        // Find matching release and determine status
        const releases = result.data?.result?.releases || [];
        const releasePolicyUrl = result.data?.result?.links?.releasePolicy || null;
        const matchingRelease = findMatchingRelease(releases, versionId);
        const statusInfo = determineStatus(matchingRelease);
        
        const badge = createStatusBadge(statusInfo, releasePolicyUrl);
        badge.id = 'eol-status-badge';
        targetElement.appendChild(badge);
        
        // Log for debugging
        console.log('EOL Checker:', {
            osId,
            versionId,
            productName,
            matchingRelease: matchingRelease?.name,
            status: statusInfo.status,
            releasePolicyUrl
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', checkEolStatus);
    } else {
        checkEolStatus();
    }
})();
