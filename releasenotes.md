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