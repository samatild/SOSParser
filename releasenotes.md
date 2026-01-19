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