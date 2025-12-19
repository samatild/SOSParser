#!/usr/bin/env python3
"""System configuration analysis from sosreport"""

from pathlib import Path
from typing import Any, Dict, List

from analyzers.docker import DockerCommandsAnalyzer
from utils.crash_directory import CrashDirectoryCollector
from utils.logger import Logger


class SystemConfigAnalyzer:
    """Analyze system configuration files from sosreport"""
    
    def analyze_general(self, base_path: Path) -> dict:
        """Analyze general system configuration"""
        Logger.debug("Analyzing general system configuration")
        
        data = {}
        
        # Hostname
        hostname_file = base_path / 'etc' / 'hostname'
        if hostname_file.exists():
            data['hostname'] = hostname_file.read_text().strip()
        
        # Timezone
        timezone_file = base_path / 'etc' / 'localtime'
        if timezone_file.exists():
            try:
                # Follow symlink to get timezone
                tz_path = timezone_file.resolve()
                tz_str = str(tz_path)
                if 'zoneinfo/' in tz_str:
                    data['timezone'] = tz_str.split('zoneinfo/')[-1]
            except Exception:
                pass
        
        # Locale
        locale_file = base_path / 'etc' / 'locale.conf'
        if locale_file.exists():
            data['locale'] = locale_file.read_text().strip()
        
        # Machine ID
        machine_id_file = base_path / 'etc' / 'machine-id'
        if machine_id_file.exists():
            data['machine_id'] = machine_id_file.read_text().strip()
        
        return data
    
    def analyze_boot(self, base_path: Path) -> dict:
        """Analyze boot configuration"""
        Logger.debug("Analyzing boot configuration")
        
        data = {}
        
        # GRUB config
        grub_cfg = base_path / 'boot' / 'grub2' / 'grub.cfg'
        if grub_cfg.exists():
            try:
                content = grub_cfg.read_text()
                data['grub_cfg'] = content[:5000]  # First 5000 chars
            except Exception as e:
                Logger.warning(f"Failed to read grub.cfg: {e}")
        
        # Kernel command line
        cmdline_file = base_path / 'proc' / 'cmdline'
        if cmdline_file.exists():
            data['cmdline'] = cmdline_file.read_text().strip()
        
        # Boot loader entries
        loader_entries = base_path / 'boot' / 'loader' / 'entries'
        if loader_entries.exists():
            entries = list(loader_entries.glob('*.conf'))
            data['loader_entries'] = [e.name for e in entries]
        
        return data
    
    def analyze_authentication(self, base_path: Path) -> dict:
        """Analyze authentication configuration"""
        Logger.debug("Analyzing authentication configuration")
        
        data = {}
        
        # nsswitch.conf
        nsswitch = base_path / 'etc' / 'nsswitch.conf'
        if nsswitch.exists():
            data['nsswitch'] = nsswitch.read_text()
        
        # PAM configuration files
        pam_dir = base_path / 'etc' / 'pam.d'
        if pam_dir.exists():
            pam_files = list(pam_dir.glob('*'))
            data['pam_files'] = [f.name for f in pam_files if f.is_file()]
        
        # SSH config
        sshd_config = base_path / 'etc' / 'ssh' / 'sshd_config'
        if sshd_config.exists():
            data['sshd_config'] = sshd_config.read_text()
        
        # Login defs
        login_defs = base_path / 'etc' / 'login.defs'
        if login_defs.exists():
            data['login_defs'] = login_defs.read_text()
        
        return data

    def analyze_ssh_runtime(self, base_path: Path) -> dict:
        """Analyze sshd -T output to capture runtime SSH configuration"""
        Logger.debug("Analyzing SSH runtime configuration from sshd -T")

        sshd_t = base_path / 'sos_commands' / 'ssh' / 'sshd_-T'
        if not sshd_t.exists():
            return {}

        try:
            content = sshd_t.read_text()
        except Exception as e:
            Logger.warning(f"Failed to read sshd_-T output: {e}")
            return {}

        grouped = {}
        order = []
        entries = []

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if ' ' in stripped or '\t' in stripped:
                key, value = stripped.split(None, 1)
                value = value.strip()
            else:
                key, value = stripped, ''

            entries.append({'option': key, 'value': value})

            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(value)

        settings = [{'option': key, 'value_list': grouped.get(key, [])} for key in order]

        runtime_data = {
            'raw': content.strip(),
            'settings': settings,
            'entries': entries,
        }

        try:
            runtime_data['source'] = str(sshd_t.relative_to(base_path))
        except Exception:
            runtime_data['source'] = str(sshd_t)

        return runtime_data
    
    def analyze_services(self, base_path: Path) -> dict:
        """Analyze systemd services"""
        Logger.debug("Analyzing systemd services")
        
        data = {}
        entries = []
        failed_entries = []
        
        # Service list from sos_commands
        service_list = base_path / 'sos_commands' / 'systemd' / 'systemctl_list-units'
        if service_list.exists():
            raw = service_list.read_text()
            data['service_list'] = raw
            lines = [l for l in raw.splitlines() if l.strip()]
            # Skip header lines until we find the column header
            for line in lines:
                if line.lower().startswith('unit '):
                    continue
                if line.startswith('LOAD '):
                    continue
                if 'units listed' in line:
                    continue
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    unit, load, active, sub, desc = parts[0:5]
                elif len(parts) >= 4:
                    unit, load, active, sub = parts[0:4]
                    desc = ''
                else:
                    continue
                entries.append({
                    'name': unit,
                    'loaded': load,
                    'active': f"{active} {sub}".strip(),
                    'description': desc,
                })
        
        # Failed services
        failed_services = base_path / 'sos_commands' / 'systemd' / 'systemctl_list-units_--failed'
        if failed_services.exists():
            raw = failed_services.read_text()
            data['failed_services'] = raw
            lines = [l for l in raw.splitlines() if l.strip()]
            for line in lines:
                if line.lower().startswith('unit '):
                    continue
                if line.startswith('LOAD '):
                    continue
                if 'failed units listed' in line:
                    continue
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    unit, load, active, sub, desc = parts[0:5]
                elif len(parts) >= 4:
                    unit, load, active, sub = parts[0:4]
                    desc = ''
                else:
                    continue
                failed_entries.append({
                    'name': unit,
                    'loaded': load,
                    'active': f"{active} {sub}".strip(),
                    'description': desc,
                })
        
        # Enabled services
        enabled_services = base_path / 'sos_commands' / 'systemd' / 'systemctl_list-unit-files'
        if enabled_services.exists():
            content = enabled_services.read_text()
            data['enabled_services'] = content[:10000]  # Limit size

        if entries:
            data['entries'] = entries
        if failed_entries:
            data['failed_services_entries'] = failed_entries
        
        return data
    
    def analyze_cron(self, base_path: Path) -> dict:
        """Analyze cron jobs"""
        Logger.debug("Analyzing cron jobs")
        
        data = {}
        
        # Crontab
        crontab = base_path / 'etc' / 'crontab'
        if crontab.exists():
            data['crontab'] = crontab.read_text()
        
        # Cron.d directory
        cron_d = base_path / 'etc' / 'cron.d'
        if cron_d.exists():
            cron_files = {}
            for cron_file in cron_d.glob('*'):
                if cron_file.is_file():
                    try:
                        cron_files[cron_file.name] = cron_file.read_text()
                    except Exception:
                        pass
            data['cron_d'] = cron_files
        
        # Cron jobs from sos_commands
        cron_cmd = base_path / 'sos_commands' / 'cron' / 'crontab_-l_-u_root'
        if cron_cmd.exists():
            data['root_crontab'] = cron_cmd.read_text()
        
        return data
    
    def analyze_security(self, base_path: Path) -> dict:
        """Analyze security configuration"""
        Logger.debug("Analyzing security configuration")
        
        data = {}
        
        # SELinux status
        selinux_status = base_path / 'sos_commands' / 'selinux' / 'sestatus_-b'
        if not selinux_status.exists():
            selinux_status = base_path / 'sos_commands' / 'selinux' / 'sestatus'
        if selinux_status.exists():
            data['selinux_status'] = selinux_status.read_text()
        
        # SELinux config
        selinux_config = base_path / 'etc' / 'selinux' / 'config'
        if selinux_config.exists():
            data['selinux_config'] = selinux_config.read_text()
        
        # Firewall status
        firewall_status = base_path / 'sos_commands' / 'firewalld' / 'firewall-cmd_--list-all-zones'
        if firewall_status.exists():
            data['firewall_zones'] = firewall_status.read_text()
        
        # Audit rules
        audit_rules = base_path / 'etc' / 'audit' / 'audit.rules'
        if audit_rules.exists():
            data['audit_rules'] = audit_rules.read_text()
        
        return data
    
    def analyze_packages(self, base_path: Path) -> dict:
        """Analyze package management"""
        Logger.debug("Analyzing package management")

        data = {}

        # RPM packages (Red Hat/CentOS/SUSE based systems)
        # Try different possible RPM file names
        rpm_files = [
            base_path / 'sos_commands' / 'rpm' / 'rpm_-qa',
            base_path / 'sos_commands' / 'rpm' / 'sh_-c_rpm_--nodigest_-qa_--qf_-59_NVRA_INSTALLTIME_date_sort_-V'
        ]

        rpm_list = None
        for rpm_file in rpm_files:
            if rpm_file.exists():
                rpm_list = rpm_file
                break

        if rpm_list:
            content = rpm_list.read_text()
            packages = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Handle different RPM output formats
                if ' ' in line:
                    # Format: package-name-version.arch date
                    package_name = line.split()[0]
                else:
                    # Format: just package name
                    package_name = line
                packages.append(package_name)

            data['rpm_count'] = len(packages)
            data['rpm_sample'] = packages[:50]  # First 50
            data['package_manager'] = 'rpm'

        # Debian packages (Debian/Ubuntu based systems)
        elif (base_path / 'sos_commands' / 'dpkg' / 'dpkg_-l').exists():
            debian_list = base_path / 'sos_commands' / 'dpkg' / 'dpkg_-l'
            content = debian_list.read_text()

            packages = []
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('Desired=') or line.startswith('||/'):
                    continue  # Skip headers

                # Parse dpkg -l format: Status|Name|Version|Architecture|Description
                parts = line.split(None, 4)  # Split on whitespace, max 5 parts
                if len(parts) >= 3:  # Need at least status, name, version
                    # Skip lines that don't start with proper status (ii, rc, etc.)
                    if len(parts[0]) >= 2 and parts[0][0].isalpha():
                        package_info = f"{parts[1]} {parts[2]}"  # name version
                        packages.append(package_info)

            data['rpm_count'] = len(packages)  # Keep compatibility with template
            data['rpm_sample'] = packages[:50]  # First 50
            data['package_manager'] = 'dpkg'

        # APT repos
        apt_sources = base_path / 'etc' / 'apt' / 'sources.list'
        if apt_sources.exists():
            data['repos'] = apt_sources.read_text()

        # DNF/YUM repos (fallback)
        dnf_repos = base_path / 'sos_commands' / 'dnf' / 'dnf_-C_repolist'
        if not dnf_repos.exists():
            dnf_repos = base_path / 'sos_commands' / 'yum' / 'yum_-C_repolist'
        if dnf_repos.exists() and 'repos' not in data:
            data['repos'] = dnf_repos.read_text()

        # Package manager config
        # APT config
        apt_conf = base_path / 'etc' / 'apt' / 'apt.conf'
        if apt_conf.exists():
            data['package_manager_conf'] = apt_conf.read_text()
        # DNF/YUM config (fallback)
        else:
            dnf_conf = base_path / 'etc' / 'dnf' / 'dnf.conf'
            if not dnf_conf.exists():
                dnf_conf = base_path / 'etc' / 'yum.conf'
            if dnf_conf.exists():
                data['package_manager_conf'] = dnf_conf.read_text()

        return data
    
    def analyze_kernel_modules(self, base_path: Path) -> dict:
        """Analyze kernel modules"""
        Logger.debug("Analyzing kernel modules")
        
        data = {}
        
        # Loaded modules
        lsmod = base_path / 'sos_commands' / 'kernel' / 'lsmod'
        if lsmod.exists():
            data['lsmod'] = lsmod.read_text()
        
        # Module parameters
        modprobe_dir = base_path / 'etc' / 'modprobe.d'
        if modprobe_dir.exists():
            modprobe_files = {}
            for mod_file in modprobe_dir.glob('*'):
                if mod_file.is_file():
                    try:
                        modprobe_files[mod_file.name] = mod_file.read_text()
                    except Exception:
                        pass
            data['modprobe_d'] = modprobe_files
        
        # Kernel parameters
        sysctl = base_path / 'sos_commands' / 'kernel' / 'sysctl_-a'
        if sysctl.exists():
            data['sysctl_all'] = sysctl.read_text()[:5000]  # First 5000 chars
        
        return data
    
    def analyze_users_groups(self, base_path: Path) -> dict:
        """Analyze users and groups"""
        Logger.debug("Analyzing users and groups")
        
        data = {}
        
        # passwd file
        passwd = base_path / 'etc' / 'passwd'
        if passwd.exists():
            data['passwd'] = passwd.read_text()
        
        # group file
        group = base_path / 'etc' / 'group'
        if group.exists():
            data['group'] = group.read_text()
        
        # sudoers
        sudoers = base_path / 'etc' / 'sudoers'
        if sudoers.exists():
            data['sudoers'] = sudoers.read_text()
        
        return data

    def analyze_crash_kdump(self, base_path: Path) -> dict:
        """Analyze crashkernel/kdump configuration and collected crash data."""
        Logger.debug("Analyzing crash and kdump data from sosreport")

        data: Dict[str, Any] = {}

        config_files = self._read_crash_config_files(base_path)
        if config_files:
            data['config_files'] = config_files

        sos_outputs = self._read_sos_kdump_commands(base_path)
        if sos_outputs:
            data['sos_commands'] = sos_outputs

        collector = CrashDirectoryCollector(base_path)
        var_crash = collector.collect(collector.discover_default_directories())
        if var_crash:
            data['var_crash'] = var_crash

        return data

    def analyze_containers(self, base_path: Path) -> dict:
        """Analyze container runtime information (docker/podman)."""
        Logger.debug("Analyzing container runtime information")
        analyzer = DockerCommandsAnalyzer(base_path)
        return analyzer.analyze()

    def _read_crash_config_files(self, base_path: Path) -> List[Dict[str, str]]:
        """Return contents of interesting crash-related config files."""
        files: List[Dict[str, str]] = []
        config_paths = [
            ("etc/sysconfig/kdump", "/etc/sysconfig/kdump"),
            ("etc/kdump.conf", "/etc/kdump.conf"),
            ("var/log/kdump.log", "/var/log/kdump.log"),
        ]

        for rel_path, display_path in config_paths:
            file_path = base_path / rel_path
            if not file_path.exists():
                continue
            content = self._read_text_with_limit(file_path)
            if content is None:
                continue
            files.append({"path": display_path, "content": content})

        return files

    def _read_sos_kdump_commands(self, base_path: Path) -> List[Dict[str, str]]:
        """Read outputs captured under sos_commands/kdump."""
        sos_dir = base_path / "sos_commands" / "kdump"
        if not sos_dir.exists():
            return []

        entries: List[Dict[str, str]] = []
        for child in sorted(sos_dir.iterdir()):
            if not child.is_file():
                continue
            content = self._read_text_with_limit(child)
            if content is None:
                continue
            entries.append({"name": child.name, "content": content})

        return entries

    def _read_text_with_limit(self, path: Path, limit: int = 200_000) -> str | None:
        """Read text from a file, truncating to a safe size."""
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                data = handle.read(limit + 1)
        except Exception as exc:
            Logger.debug(f"Failed to read {path}: {exc}")
            return None

        if len(data) > limit:
            return data[:limit] + "\n... truncated ..."
        return data
