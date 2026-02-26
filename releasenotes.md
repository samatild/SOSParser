## [0.2.25] - 2026-02-26

### Added
- **Top-line Health Summary Card**: A prominent status card is now displayed at the top of the Summary tab whenever issues are detected.
  - Shows overall status badge: **Critical**, **Warnings**, or hidden when the system is healthy (no noise on clean systems)
  - Counts of critical and warning findings displayed inline
  - Each finding shows category, title, detail, and a click-to-navigate link to the relevant report tab
  - Evidence panel shows the exact **file path**, **line number**, and **full matched line** from the diagnostic bundle

- **Rules Engine**: A file-based known-issue detection engine that scales without code changes.
  - Loads all `*.json` rule collections from `src/rules/known_issues/` at runtime 
  - Each rule specifies: target file paths per format (`sosreport` / `supportconfig` / `both`), a Python regex, severity, category, title template, detail, minimum match threshold, and section link
  - Scans files line-by-line and captures up to 10 evidence lines per finding (file, line number, full text)
  - Supports regex flags: `IGNORECASE`, `MULTILINE`, `DOTALL`
  - Schema documented in [`src/rules/README.md`](src/rules/README.md)

- **Built-in Known-Issue Collections** (`src/rules/known_issues/`): 6 collections, 24 rules covering:
  - `kernel_issues.json` — Kernel panic, Oops, BUG assertion, call trace, tainted kernel
  - `memory_issues.json` — OOM killer invocation, page allocation failures
  - `storage_issues.json` — XFS/EXT4/Btrfs errors, read-only remount, I/O errors, SMART warnings
  - `network_issues.json` — NIC link-down, network unreachable, RX/TX errors, NFS stale handle
  - `security_issues.json` — Segfaults, brute-force auth failures, AppArmor denials, SELinux AVC denials
  - `service_issues.json` — Service crash-loops, systemd coredumps, service start timeouts
