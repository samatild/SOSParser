## [0.2.26] - 2026-02-27

### Added
- **In-report Search Overlay**: Press `/` (or `Ctrl+Shift+F`) anywhere in a generated report to open a floating search panel.
  - Displays a scrollable results list with `Tab → Subtab` breadcrumb location and a text snippet for each match
  - Clicking a result navigates directly to it, activating the correct tab and subtab automatically
  - Keyboard navigation: `Enter` / `Shift+Enter`, `↑` / `↓` arrows cycle through results; `Escape` closes
  - Debounced input (220 ms); up to 200 results shown in the panel
  - Search hint (`Press / to search`) displayed right-aligned in the tab bar
  - Fully CSP-compliant — all logic in `main.js`, no inline handlers

### Changed
- **`docker-build.sh`**: Added `--run-fast` mode that builds with Docker layer cache (vs. `--run` which always builds `--no-cache`), then restarts the container — useful for rapid iteration on Python/template changes
- Fixed "Failed / Inactive Services" table in System Config tab not rendering when `systemctl` reported "0 loaded units listed" (Jinja2 string-as-sequence false-positive)