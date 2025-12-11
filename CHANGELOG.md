# Changelog

All notable changes to SOSParser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Scenario-based detection improvements
- Performance optimizations for large reports

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

[Unreleased]: https://github.com/samatild/SOSParser/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/samatild/SOSParser/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/samatild/SOSParser/releases/tag/v0.1.0
