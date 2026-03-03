## [0.3.0] - 2026-03-03

### Added
- **System Timezone in Report Summary Card**: The system timezone is now displayed in the System Information card at the top of every report, for both sosreport and supportconfig formats.
  - **sosreport**: Extracted using a 3-step fallback chain — `sos_commands/systemd/timedatectl` (`Time zone:` line, most reliable), `/etc/timezone` plain-text file (Debian/Ubuntu), `/etc/localtime` symlink resolution (last resort)
  - **supportconfig**: Extracted from the `timedatectl` command block inside `ntp.txt` (`Time zone:` field)
  - Timezone is exposed at the top level of `system_config` for both formats and conditionally rendered in the template