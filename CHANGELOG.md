# Changelog

All notable changes to SOSParser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Performance optimizations for large reports

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

[Unreleased]: https://github.com/samatild/SOSParser/compare/v0.2.5...HEAD
[0.2.5]: https://github.com/samatild/SOSParser/releases/tag/v0.2.5
[0.2.4]: https://github.com/samatild/SOSParser/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/samatild/SOSParser/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/samatild/SOSParser/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/samatild/SOSParser/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/samatild/SOSParser/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/samatild/SOSParser/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/samatild/SOSParser/releases/tag/v0.1.0
