# Changelog

All notable changes to SOSParser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Performance optimizations for large reports
- Additional filesystem analyzers (Btrfs, XFS, ZFS)
- Advanced security analysis modules
- Custom scenario configuration via JSON

## [0.2.22] - 2026-02-09

### Added
- **Audit Logging for Public Mode**: Comprehensive security and usage monitoring
  - Automatically enabled when `PUBLIC_MODE=true`
  - Logs all page access, file uploads, report generation, and report viewing
  - Structured JSON format to stdout for easy integration
  - Client IP, user agent, timestamps, and event details captured

---

## [0.2.21] - 2026-02-06

### Fixed
- **Diagnostic Date Display**: Fixed incorrect date display in report header and metadata
  - Header now shows "Diagnostic Date" with the actual date when sosreport/supportconfig was collected
  - Report Metadata section now shows both "Data Collected" (when diagnostic was taken) and "Report Generated" (when HTML report was created)
  - For sosreport: Parses `sos_logs/ui.log` for the collection timestamp
  - For supportconfig: Parses `basic-environment.txt` `/bin/date` command output

---

## [0.2.20] - 2026-02-04

### Added
- **Process Information (SOS and SCC)**: New Processes tab with detailed process analysis for both sosreport and supportconfig
  - **Subtabs**: Process Tree (collapsible pstree), Process Utilization (ps snapshots), Process IO, Process Handlers (lsof), Process Stats (pidstat)

- **SAR Dynamic Graphs**: New SAR tab with interactive time-series charts for both sosreport and supportconfig
  - **Single dynamic graph** with dropdown selector organized by category
  - **18 metric categories**: CPU Utilization, CPU Per-Core, Process Creation, Softnet, Memory, Swap, Swap Paging, Hugepages, Paging, I/O Transfer, Block Device, Filesystem, Network Interface, Network Errors, Sockets, NFS Client/Server, Load Average, TTY
  - **CPU Per-Core chart**: Individual utilization line per core with auto-generated colors
  - **Day navigation**: Dropdown + Previous/Next buttons with actual dates (e.g., "Dec 11, 2025")
  - **Supportconfig support**: Parses `sar/` directory (both `.xz` compressed and uncompressed files)
  - Implemented with Chart.js; fixed-height canvas

---

## [0.2.19] - 2026-02-02

### Fixed
- **Critical Memory Optimization for Supportconfig**: Reduces peak memory from ~3.2GB to ~150MB
  - `boot.txt` streaming: New `find_sections_streaming()` method reads large files line-by-line
  - `BootConfigAnalyzer` now streams through boot.txt finding only needed sections (was loading entire file)
  - `ProviderDetector` fixed to read only first N bytes instead of loading entire file then truncating
  - `get_kernel_info()` uses streaming to find "running kernel" section without loading boot.txt
  - Peak memory during supportconfig analysis reduced from 946MB to ~150MB

### Added
- **Memory Profiling Tools** (debug mode only):
  - `Logger.memory(phase)` - logs RSS and Peak memory at checkpoints
  - Tracks VmHWM (High Water Mark) to catch transient memory spikes
  - Granular tracking in all supportconfig sub-analyzers
  - Enable with `WEBAPP_DEBUG=1` environment variable

---

## [0.2.18] - 2026-02-02

### Fixed
- **Memory Efficiency for Large Log Files**: Prevents OOM crashes in Kubernetes pods
  - Log file tailing now uses reverse-reading algorithm for files > 1MB
  - Only reads the last N lines from disk instead of loading entire file into memory
  - Gzip log files now stream through with `deque(maxlen=N)` to cap memory usage
  - Supportconfig parser uses same memory-efficient tail algorithm
  - Chunk reassembly uses streaming copy (`shutil.copyfileobj`) with 64KB buffer
  - Fixes OOM issues when processing sosreports with large journal/message logs

---

## [0.2.17] - 2026-02-02

### Added
- **Historical Log Files Support**: System logs now include rotated/archived log files
  - Automatically reads gzipped log files (`.gz`) when main log file is missing
  - Falls back to latest rotated file if primary log doesn't exist
  - Shows up to 5 historical log files in collapsible sections
  - Displays date and "gzip" badge for compressed files
  - Configurable line limit for historical logs (`LOG_LINES_HISTORICAL`, default: 500)

- **Boot Log Display**: Added `/var/log/boot.log` to System Logs tab

### Fixed
- **Uptime Always Showing "Unknown"**: Fixed uptime detection for sosreport
  - Now checks correct path `sos_commands/host/uptime` first
  - Converts raw uptime to human-readable format (e.g., "4 hours, 47 minutes" or "45 days, 3 hours, 22 minutes")
  - Supports various uptime formats including days, hours:minutes, and minutes only

- **Oracle Linux Logo Showing as Fedora**: Fixed logo priority order
  - Oracle Linux has `ID_LIKE="fedora"` which caused incorrect Fedora logo match
  - Moved Oracle detection before Fedora in priority list

- **Kubernetes Log Streaming**: Logs now properly appear in `kubectl logs`
  - Added `flush=True` to all log output for immediate streaming
  - Added gunicorn flags: `--access-logfile -`, `--error-logfile -`, `--capture-output`

---

## [0.2.16] - 2026-01-28

### Added
- **Visual Disk Usage Graphs**: Summary page now displays disk usage with color-coded progress bars
  - Green: < 50% used
  - Blue: 50-75% used
  - Orange: 75-90% used
  - Red: > 90% used
  - Filters out virtual filesystems for cleaner display
  - Raw `df` output available in collapsible details section

- **Memory Usage Pie Chart**: Visual breakdown of memory allocation on Summary page
  - Donut chart showing Used (red), Buffers/Cache (blue), and Free (green) memory
  - Total RAM displayed in center
  - Legend with human-readable values and percentages
  - Available Memory progress bar with color coding (green/orange/red)
  - Swap usage progress bar
  - vmstat displayed alongside memory chart in 2-column layout
  - Raw `free` output available in collapsible details section

### Fixed
- **Packages List Truncation**: System Config → Packages now shows full package list instead of first 50 only
  - Scrollable container for long package lists (max-height 400px)
  - Shows package count with package manager type

- **System Config → General Tab Empty for sosreport**: Tab now properly populated with:
  - Collection time, uname, uptime
  - OS release information
  - Kernel tainted status
  - CPU vulnerabilities
  - Memory info (free), disk usage (df -h/-i)
  - Process snapshot
  - Virtualization detection

- **Oracle Linux Identification**: Added 'ol' ID variant recognition
  - EOL checker now correctly identifies Oracle Linux systems
  - Logo properly displayed instead of "Unknown Distribution"

### Changed
- **CPU Details Section**: Moved to bottom of Summary page for better information hierarchy

---

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

---

## [0.2.14] - 2026-01-22

### Added
- **Configurable Log Line Limits**: Log parsing now reads significantly more lines with configurable limits
  - Default increased from 100-200 lines to **1000 lines** for much more log context
  - Configurable via environment variables for Docker deployments:
    - `LOG_LINES_DEFAULT`: Fallback default (1000)
    - `LOG_LINES_PRIMARY`: Primary logs like messages, syslog, dmesg, journal (1000)
    - `LOG_LINES_SECONDARY`: Secondary logs like cron, mail, boot (500)
  - Works for both sosreport and supportconfig formats
  - Browser-safe defaults (recommended max: 5000 lines)

## [0.2.13] - 2026-01-15

### Added
- **LVM Topology Visualization**: New SVG diagram showing LVM structure in the Filesystem → LVM tab
  - Visual representation of Physical Volumes (PV) → Volume Groups (VG) → Logical Volumes (LV)
  - Color-coded boxes: red for PVs, green for VGs, blue for LVs
  - Displays size information for each component
  - Multi-row layout for systems with many LVs (max 4 per row to prevent horizontal overflow)
  - Pure SVG implementation with no external dependencies
  - Works for both sosreport and supportconfig formats

### Fixed
- **LVM Data Not Showing (sosreport)**: Fixed LVM subtab showing empty for sosreport files
  - Updated file matching to use glob patterns (`pvs_*`, `vgs_*`, `lvs_*`) instead of exact filenames
  - sosreport command output filenames vary by version and include full command arguments
  - Added support for `vgdisplay`, `pvdisplay`, `lvdisplay` detailed output files

---

## [0.2.12] - 2026-01-15

### Added
- **Public Mode**: New deployment mode for public-facing instances with enhanced privacy
  - Enable via `PUBLIC_MODE=true` environment variable (Docker runtime configurable)
  - Reports are generated once, displayed once, then automatically deleted
  - "Saved Reports" browser hidden from UI
  - Report listing and deletion API endpoints disabled
  - Output directory cleaned on startup (no leftover data from crashes)
  - Ideal for public demo deployments where no data should be retained

### Changed
- **Build Script**: Added `--run-public` parameter to `docker-build.sh` for quick public mode testing
- **Documentation**: Updated README with Public Mode vs Private Mode deployment instructions

---

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

---

## [0.2.10] - 2026-01-13

### Added
- **Chunked File Upload System**: Large files are now uploaded in 5MB chunks to prevent timeout issues on slow networks
  - New backend API endpoints (`/api/upload/init`, `/api/upload/chunk`, `/api/upload/complete`)
  - File-based session storage for multi-worker compatibility
  - Automatic cleanup of stale upload sessions
- **Real-time Upload Progress**: Users can now see detailed upload progress including:
  - Progress bar with percentage
  - Upload speed (e.g., "2.5 MB/s")
  - Bytes transferred (e.g., "125 MB / 500 MB")
  - Estimated time remaining
  - Cancel upload button
- **Live Console Output**: Collapsible terminal-style console panel during analysis
  - Real-time log streaming via Server-Sent Events (SSE)
  - Background analysis execution with stdout/stderr capture
  - Auto-scrolling console with clear button
  - Color-coded messages (info, success, error, warning)
- **README**: Added demo

### Changed
- **Gunicorn Timeout**: Increased worker timeout to 30 minutes (1800s) for large file extraction and analysis
- **Build Script**: `docker-build.sh` now builds with `--no-cache` by default for reliable deployments
- **Log Level**: Web interface now shows INFO/WARNING/ERROR messages only (debug messages hidden)

### Fixed
- **Multi-worker Session Bug**: Upload sessions now use file-based storage instead of in-memory, fixing issues where different gunicorn workers couldn't find upload sessions

---

## [0.2.9] - 2026-01-05

## Added
- **NTP SCC Implementation**: Added support for NTP configuration on Support Config
---

## [0.2.8] - 2025-12-22

## Added
- **sssd Implementation**: Added support for Security Security Services daemon for both SOSReport and Supportconfig

## Security Improvements
- **zipp**: Webapp also pinned to 3.19.1 to avoid vulnerability

---

## [0.2.7] - 2025-12-19

## Added
- **Crash Dump Support**: Added support for kdump collected files and respective configuration, for both sosreports and support config.

## Fixes
- **UI: Navigation Tweaks**: Default page is always "Overview" tab; Clicking logo/title redirects to document root.

## Security Improvements
- **Jinja2**: Updated from 3.1.2 to 3.1.6
- **zipp**: Pinned to 3.19.1 to avoid vulnerability
- **gunicorn**: Updated from 21.2.0 to 23.0.0

---

## [0.2.6] - 2025-12-18

### Added
- **NFS Analysis for Supportconfig**: Added comprehensive NFS client and server analysis including package verification, service status, configuration parsing, statistics, mounts, and exports - displayed in dedicated NFS subtab under Filesystem tab
- **Samba/CIFS Analysis for Supportconfig**: Added Samba package analysis, verification status, configuration parsing, and service monitoring - displayed in dedicated Samba subtab under Filesystem tab

---

## [0.2.5] - 2025-12-16

### Added
- **Debian Package Support**: Added Debian package parsing (`dpkg -l`) for SOSReport when RPM packages are not available, supporting both Red Hat/CentOS/SUSE (RPM) and Debian/Ubuntu (DPKG) based systems

---

## [0.2.4] - 2025-12-15

### Added
- **Enhanced Summary Pages**: Rich overview pages for both supportconfig and SOSReport formats featuring system resources (disk usage, memory, virtual memory), top CPU/memory consumers, CPU security vulnerabilities, and kernel status information
- **Logo Logic Enhancement**: Improved distribution logo detection and display logic with support for additional Linux distributions

### Refactored
- **Summary Analyzer Architecture**: Extracted summary data extraction logic into dedicated `SupportconfigSummaryAnalyzer` and `SOSReportSummaryAnalyzer` classes for better separation of concerns and maintainability
- **Modular Analyzer Structure**: Reorganized analyzer components into focused, format-specific modules improving code organization and testability

---

## [0.2.3] - 2025-12-13

### Added
- SSH configuration analysis: Parse `sos_commands/ssh/sshd_-T` (effective SSH configuration) and load this data in both SOS and supportconfig flows (`system_config.ssh_runtime`) for template access
- System Configuration UI enhancement: New dedicated "SSH" subtab that renders a directive table plus raw `sshd -T` text
- Docker build script improvement: Added `-run` flag to `./docker-build.sh` that stops and removes existing sosparser container on dev/test systems and runs a new one for simplified testing

---

## [0.2.2] - 2025-12-12

### Added
- Saved reports browser in the web UI with open/delete actions and a GitHub header link.
- API endpoints to list and delete saved reports.
- Dockerfile volumes and README instructions for persisting uploads/outputs.

### Changed
- Reports are no longer deleted after viewing; outputs persist for browsing.
- Report viewer rewrites asset href/src for images (including favicon) to ensure icons load.
- Home header title is plain text (no link) per UX request; GitHub icon uses inline SVG.

### Fixed
- Report discovery now searches nested token subfolders so saved reports display in the browser panel.

---

## [0.2.1] - 2025-12-11

### Added
- Container runtime reporting (Docker): parsing via `DockerCommandsAnalyzer` wired into both sosreport and supportconfig analyzers, surfaced in a new Containers subtab (docker version/info/ps/ps -a/stats/images/networks/volumes/inspect/events/journal/config).
- CSP nonces for inline scripts in generated reports plus stricter response headers.

### Changed
- Jinja environment now auto-escapes HTML/XML templates for safer rendering.
- Report serving paths resolved to prevent path traversal when fetching reports.

### Fixed
- Workflow triggers restricted to `push` on `main` only (build-on-main).

---

## [0.2.0] - 2025-12-11

### Added
- Supportconfig end-to-end parsing and report rendering across tabs (boot, authentication, services, cron, security, packages, kernel parameters, general, filesystem, network, logs, cloud) using the sample `scc_sles15_251211_1144` bundle.
- Network connectivity, DNS/hosts, firewall, routing, interfaces, and connectivity subtabs populated for supportconfig.
- Cloud tab metadata subtab with Azure/public cloud details from `public_cloud/` (metadata, instance init, hosts, cloudregister, credentials, osrelease).
- Helper `generate_supportconfig_example_report` for rapid local testing of the example supportconfig archive.

### Changed
- Jinja report template updated with safer `is mapping` / `is sequence` guards and new subtabs (connectivity, metadata) to avoid `.items()` errors on sosreport data.
- Filesystem, network, and system config analyzers now return structured dictionaries aligned with template expectations (e.g., mounts, LVM, filesystems, services, cron, security, packages, kernel modules, general).
- Docker runtime uses Gunicorn (`webapp.wsgi:application`) and Flask debug disabled by default.

### Fixed
- Resolved Jinja `TemplateSyntaxError` due to missing `{% endif %}` in services section.
- Fixed `ModuleNotFoundError` for Gunicorn by using absolute import in `webapp/wsgi.py`.
- Prevented `'str' object has no attribute 'items'` during sosreport rendering by adding type checks in the template.

---

## [0.1.0] - 2025-12-11

### Initial Release

First public release of SOSParser - a comprehensive Linux sosreport analyzer.

### Added

#### Core Features
- **Web-based Upload Interface**: Simple drag-and-drop file upload for sosreport archives
- **Automated Analysis Engine**: Extracts and analyzes system diagnostic information
- **Interactive HTML Reports**: Dark-themed, tabbed reports with rich system information

#### Analysis Modules
- **System Information**
  - CPU, memory, and disk information
  - DMI/BIOS details
  - System load and uptime
  - OS identification with distro logos (Ubuntu, RHEL, CentOS, SUSE, Oracle Linux)

- **System Configuration**
  - Package management (RPM/DNF/YUM)
  - Kernel modules and parameters
  - Users, groups, and sudoers configuration

- **Filesystem Analysis**
  - Mount points and filesystem types
  - Disk usage statistics
  - LVM configuration (PV, VG, LV)

- **Network Analysis**
  - Network interfaces and IP configuration
  - Routing tables
  - DNS configuration
  - Firewall rules (iptables, firewalld)

- **Cloud Provider Detection**
  - Automatic detection of AWS, Azure, GCP, Oracle Cloud
  - Cloud-init configuration analysis
  - Provider-specific metadata and agent logs

- **Advanced Log Viewer**
  - Interactive log viewing with syntax highlighting
  - Search functionality (text, regex, case-sensitive, whole word)
  - Log level filtering (ERROR, WARNING, INFO, DEBUG)
  - Line-by-line navigation
  - Copy and download capabilities
  - Support for: system logs, kernel logs, authentication logs, service logs

#### Technical Features
- **Docker Support**
  - Official Docker Hub image: `samuelmatildes/sosparser`
  - Multi-platform support (linux/amd64, linux/arm64)
  - Health checks and environment configuration
  
- **CI/CD Pipeline**
  - GitHub Actions workflow for automated builds
  - Automatic Docker Hub publishing on push to main
  - Version-based tagging

- **Format Support**
  - `.tar.xz` (recommended)
  - `.tar.gz`
  - `.tar.bz2`
  - `.tgz`
  - `.tar`

- **Privacy-Focused**
  - Automatic cleanup of uploaded files after viewing
  - No data retention
  - Local processing only

#### UI/UX
- **Ultra-Dark Condensed Theme**
  - Custom cyan/orange color scheme for webapp
  - Purple/cyan accents for reports
  - Space-efficient layout
  - Optimized for readability

- **Responsive Design**
  - Mobile-friendly interface
  - Adaptive layouts
  - Touch-optimized controls

- **Distro Logo Detection**
  - Automatic OS logo display in reports
  - Support for major Linux distributions

### Technical Details

- **Language**: Python 3.10+
- **Web Framework**: Flask 3.0
- **Templating**: Jinja2
- **Architecture**: Domain-based separation (webapp + analyzer)
- **Dependencies**: Minimal (Flask, Werkzeug, MarkupSafe)

### Known Limitations

- Currently only supports sosreport format (supportconfig coming soon)
- Scenario-based detection is limited in this release
- Large sosreports (>2GB) may take several minutes to process

### Docker Tags

- `samuelmatildes/sosparser:0.1.0` - This release
- `samuelmatildes/sosparser:latest` - Latest stable

---

## Release Notes Format

Future releases will include:

### [Version] - YYYY-MM-DD

#### Added
- New features

#### Changed
- Changes to existing functionality

#### Deprecated
- Features that will be removed in future versions

#### Removed
- Removed features

#### Fixed
- Bug fixes

#### Security
- Security-related changes

---

## Links

- **GitHub Repository**: https://github.com/samatild/SOSParser
- **Docker Hub**: https://hub.docker.com/r/samuelmatildes/sosparser
- **Issue Tracker**: https://github.com/samatild/SOSParser/issues

---

[Unreleased]: https://github.com/samatild/SOSParser/compare/v0.2.21...HEAD
[0.2.21]: https://github.com/samatild/SOSParser/releases/tag/v0.2.21
[0.2.20]: https://github.com/samatild/SOSParser/compare/v0.2.20...v0.2.21
[0.2.19]: https://github.com/samatild/SOSParser/compare/v0.2.19...v0.2.20
[0.2.18]: https://github.com/samatild/SOSParser/compare/v0.2.18...v0.2.19
[0.2.17]: https://github.com/samatild/SOSParser/releases/tag/v0.2.17
[0.2.16]: https://github.com/samatild/SOSParser/compare/v0.2.16...v0.2.17
[0.2.15]: https://github.com/samatild/SOSParser/compare/v0.2.15...v0.2.16
[0.2.14]: https://github.com/samatild/SOSParser/compare/v0.2.14...v0.2.15
[0.2.13]: https://github.com/samatild/SOSParser/compare/v0.2.13...v0.2.14
[0.2.12]: https://github.com/samatild/SOSParser/compare/v0.2.12...v0.2.13
[0.2.11]: https://github.com/samatild/SOSParser/compare/v0.2.11...v0.2.12
[0.2.10]: https://github.com/samatild/SOSParser/compare/v0.2.10...v0.2.11
[0.2.9]: https://github.com/samatild/SOSParser/compare/v0.2.9...v0.2.10
[0.2.8]: https://github.com/samatild/SOSParser/compare/v0.2.8...v0.2.9
[0.2.7]: https://github.com/samatild/SOSParser/compare/v0.2.7...v0.2.8
[0.2.6]: https://github.com/samatild/SOSParser/compare/v0.2.6...v0.2.7
[0.2.5]: https://github.com/samatild/SOSParser/compare/v0.2.5...v0.2.6
[0.2.4]: https://github.com/samatild/SOSParser/compare/v0.2.4...v0.2.5
[0.2.3]: https://github.com/samatild/SOSParser/compare/v0.2.3...v0.2.4
[0.2.2]: https://github.com/samatild/SOSParser/compare/v0.2.2...v0.2.3
[0.2.1]: https://github.com/samatild/SOSParser/compare/v0.2.1...v0.2.2
[0.2.0]: https://github.com/samatild/SOSParser/compare/v0.2.0...v0.2.1
[0.1.0]: https://github.com/samatild/SOSParser/compare/v0.1.0...v0.2.0
