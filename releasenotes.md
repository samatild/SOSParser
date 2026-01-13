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