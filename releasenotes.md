## [0.2.20] - 2026-02-04

### Added
- **Process Information (SOS and SCC)**: New Processes tab with detailed process analysis for both sosreport and supportconfig
  - **Subtabs**: Process Tree (collapsible pstree), Process Utilization (ps snapshots), Process IO, Process Handlers (lsof), Process Stats (pidstat)

- **SAR Dynamic Graphs**: New SAR tab with interactive time-series charts for both sosreport and supportconfig
  - **Single dynamic graph** with dropdown selector organized by category
  - **18 metric categories**: CPU Utilization, CPU Per-Core, Process Creation, Softnet, Memory, Swap, Swap Paging, Hugepages, Paging, I/O Transfer, Block Device, Filesystem, Network Interface, Network Errors, Sockets, NFS Client/Server, Load Average, TTY
  - **CPU Per-Core chart**: Individual utilization line per core with auto-generated colors
  - **Day navigation**: Dropdown + Previous/Next buttons with actual dates (e.g., "Dec 11, 2025")
  - **Supportconfig support**: Parses `sar/` directory (both `.xz` compressed and uncompressed files)
  - Implemented with Chart.js; fixed-height canvas
