## [0.2.22] - 2026-02-09

### Added
- **Audit Logging for Public Mode**: Comprehensive security and usage monitoring
  - Automatically enabled when `PUBLIC_MODE=true`
  - Logs all page access, file uploads, report generation, and report viewing
  - Structured JSON format to stdout for easy integration
  - Client IP, user agent, timestamps, and event details captured
