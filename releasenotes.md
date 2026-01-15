## [0.2.11] - 2026-01-15

### Added
- **OS End-of-Life Status Badge**: Reports now display a real-time support status badge next to the OS version in the header
  - Client-side integration with [endoflife.date](https://endoflife.date) API (no server load)
  - Color-coded badges: green (Supported/LTS), red (End of Life), orange (Extended Support), gray (Unknown)
  - Clickable badge links to the distribution's official release policy page
  - Supports major distributions: RHEL, CentOS, Rocky, AlmaLinux, Fedora, Oracle Linux, Debian, Ubuntu, SLES, openSUSE, Amazon Linux, Alpine, Arch
  - Works for both sosreport and supportconfig formats

### Changed
- **Content Security Policy**: Added `connect-src` directive to allow browser-side API calls to endoflife.date