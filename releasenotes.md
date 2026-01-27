## [0.2.15] - 2026-01-27

### Added
- **New Updates Tab**: Comprehensive package update and repository information analysis
  - New main navigation tab displaying package manager data for all supported formats
  - **DNF Support (RHEL 8+, Fedora)**:
    - Available updates with summary statistics (total, security, bugfix, severity counts)
    - Security advisories with CVE details
    - Repository list and verbose repository information
    - Update history
    - DNF modules (installed and available)
    - Package problems and duplicate detection
  - **APT Support (Debian, Ubuntu)**:
    - APT sources from `/etc/apt/sources.list` and `sources.list.d/`
    - Mirror configuration
    - Package pinning (preferences)
    - Held packages
    - APT policy and cache statistics
    - APT configuration dump
  - **YUM Support (RHEL 7 and older)**:
    - Repository list and update history
  - **Zypper Support (SUSE/SLES - supportconfig)**:
    - Patch summary with security/recommended/optional counts
    - Available patches and patch check status
    - Package updates list with count
    - Repository and services (modules) configuration
    - Package locks
    - Installed products and SUSEConnect subscription status
    - Product lifecycle information
    - Orphaned packages detection