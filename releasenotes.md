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