## [0.2.21] - 2026-02-06

### Fixed
- **Diagnostic Date Display**: Fixed incorrect date display in report header and metadata
  - Header now shows "Diagnostic Date" with the actual date when sosreport/supportconfig was collected
  - Report Metadata section now shows both "Data Collected" (when diagnostic was taken) and "Report Generated" (when HTML report was created)
  - For sosreport: Parses `sos_logs/ui.log` for the collection timestamp
  - For supportconfig: Parses `basic-environment.txt` `/bin/date` command output