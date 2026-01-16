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