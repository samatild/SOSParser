## Project Structure
- `webapp/`: Flask entry (`app.py`), routes/templates/static; WSGI entry (`wsgi.py`).
- `src/core/`: Orchestration (`analyzer.py`) and upload/run entry (`run_analysis`, `generate_supportconfig_example_report`).
- `src/analyzers/`: Domain analyzers.
  - `supportconfig/`: parsers for supportconfig (system_config, filesystem, network, parser, system_info).
  - `system/`: sosreport analyzers (system_config, system_info).
  - `filesystem`, `network`, `logs`, `cloud`: shared helpers for both formats.
- `src/reporting/`: `report_generator.py` builds the data model and renders Jinja.
- `src/templates/`: `report_template.html` plus JS/CSS assets.
- `src/utils/`: format detection, logging, file I/O helpers.
- `examples/`: sample supportconfig bundle (`scc_sles15_251211_1144`).

## Request Flow (Upload → Report)
1. `webapp/app.py` routes (`/`, upload handler) receive an archive and hand off to `src/core/analyzer.run_analysis`.
2. `run_analysis` detects format via `src/utils/format_detector.py` and dispatches:
   - sosreport → `analyze_sosreport` (uses `src/analyzers/system/*`).
   - supportconfig → `analyze_supportconfig` (uses `src/analyzers/supportconfig/*`).
3. Each analyzer assembles structured dictionaries (system info, system_config, filesystem, network, logs, cloud).
4. `src/reporting/report_generator.py` renders `src/templates/report_template.html` into the final HTML report.
5. Outputs are written under the configured outputs directory (`webapp/outputs` by default).

## sosreport Processing
- Detected via `format_detector`.
- Parsing: `src/analyzers/system/system_info.py` and `system_config.py` for system config/services; shared analyzers for filesystem, network, logs, cloud.
- Rendering: same `report_template.html`; template guards handle mixed types (strings vs mappings).

## supportconfig Processing
- Detected via `format_detector`.
- Parsing: `src/analyzers/supportconfig/parser.py` reads extracted files; `system_config.py`, `filesystem.py`, `network.py`, `system_info.py` map supportconfig outputs into structured dicts; logs handled in `core/analyzer.analyze_supportconfig`.
- Rendering: same template; subtabs populated for boot, auth, services, cron, security, packages, kernel params, general, filesystem, network (including connectivity), logs, and cloud metadata.

### supportconfig Section Map (source → parser → template)
- Boot: `boot.txt` → `supportconfig/system_config.get_boot_config` → `system_config.boot` → Boot tab.
- Authentication: `ssh.txt` → `get_ssh_config` → `system_config.authentication` → Authentication tab.
- Services: `systemd-status.txt` → `get_services_config` → `system_config.services.entries` / `failed_services_entries` → Services tab.
- Cron/At: `cron.txt` → `get_cron_config` → `system_config.cron` → Cron tab.
- Security: `security-selinux.txt`, `security-apparmor.txt`, `security-audit.txt` → `get_security_config` → `system_config.security` → Security tab.
- Packages: `rpm.txt` → `get_packages_config` → `system_config.packages` → Packages tab.
- Kernel params/modules: `env.txt` → `get_kernel_modules_config` → `system_config.kernel_modules` → Kernel tab.
- General: `basic-environment.txt`, `basic-health-check.txt` → `get_general_config` → `system_config.general` (+ `system_info`) → General tab.
- Filesystem: `fs-diskio.txt`, `lvm.txt`, `etc.txt` → `supportconfig/filesystem` (`get_mounts`, `get_disk_usage`, `get_lvm_info`, `get_filesystem_types`) → `filesystem` dict → Filesystem tab.
- Network: `network.txt`, fallback `etc.txt` → `supportconfig/network` (`get_interfaces`, `get_routes`, `get_dns_config`, `get_firewall_info`, `get_connectivity`, `get_networkmanager`) → `network` dict → Network tab.
- Logs: `messages*.txt`, `boot.txt`, `security-audit.txt` → `core/analyzer.analyze_supportconfig` → `logs.system`, `logs.kernel.dmesg`, `logs.auth.audit_log` → Logs tab.
- Cloud: `public_cloud/*` (metadata, instanceinit, hosts, cloudregister, credentials, osrelease) → `core/analyzer.analyze_supportconfig` → `cloud` dict (provider + azure fields) → Cloud tab (metadata subtab).

## Fast Local Test Method
- Use `generate_supportconfig_example_report` in `src/core/analyzer.py`.
- Purpose: mimic an upload using the sample bundle at `examples/scc_sles15_251211_1144/` (recreates `scc_sles15_251211_1144.txz` if missing), then runs `run_analysis` and writes a report to a test output folder.
- Call with `python3 -c "from src.core.analyzer import generate_supportconfig_example_report; generate_supportconfig_example_report()"` to produce a fresh report without the web UI.
