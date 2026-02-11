## [0.2.23] - 2026-02-11

### Added
- **Journalctl Log Support for Debian-based Systems**: Enhanced log parsing for systems without traditional `/var/log/messages` or `/var/log/syslog`
  - Automatically discovers and parses all `journalctl` outputs from `sos_commands/logs/` and `sos_commands/systemd/`
  - Supports multiple journalctl files: complete journal, current boot, previous boots
  - Intelligent fallback: When traditional logs are absent, journalctl logs are displayed in System Logs tab with informational banner
  - Parses: `journalctl_--no-pager`, `journalctl_--no-pager_--boot`, `journalctl_--no-pager_--boot_-1`, etc.
  - Each journal file displayed in collapsible section with human-readable descriptions

- **Boot History in System Config**: Added boot history tracking to Boot & GRUB section
  - Displays `journalctl --list-boots` output showing all system reboots with timestamps and boot IDs
  - Helps correlate system issues with specific boot sessions
  - Appears in System Config → Boot & GRUB tab
