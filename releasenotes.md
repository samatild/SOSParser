## [0.2.27] - 2026-02-27

### Added
- **SAR Day Selector**: After uploading a bundle, if SAR files are detected the upload overlay now shows an interactive day-picker before analysis starts.
  - Peeks inside the tarball without full extraction (`peek_sar_files`) to list SAR filenames and human-readable dates
  - All days are pre-checked; user can deselect individual days or use "Select all" / "Deselect all"
  - Clicking "Start Analysis" passes only the chosen filenames through the full pipeline (`run_analysis` → `SOSReportAnalyzer` → `SarAnalyzer.analyze(allowed_files=[...])`)
  - An empty selection skips SAR entirely — prevents runaway analysis times on large supportconfig bundles with many SAR files
  - New Flask endpoint `/api/upload/start-analysis` resumes the background analysis thread after the selection step

### Changed
- Search overlay now also indexes `h2`–`h5` section headings and `th` table headers, making titles like "Mount Points" and paths like `/etc/fstab` searchable
- Removed the "Analyze SAR data" checkbox from the upload form — the SAR selector screen is the right place for that decision