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