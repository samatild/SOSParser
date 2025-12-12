#!/usr/bin/env python3
"""System configuration analysis from sosreport"""

from pathlib import Path
from analyzers.docker import DockerCommandsAnalyzer
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
        
        # RPM packages
        rpm_list = base_path / 'sos_commands' / 'rpm' / 'rpm_-qa'
        if rpm_list.exists():
            packages = rpm_list.read_text().splitlines()
            data['rpm_count'] = len(packages)
            data['rpm_sample'] = packages[:50]  # First 50
        
        # DNF/YUM repos
        dnf_repos = base_path / 'sos_commands' / 'dnf' / 'dnf_-C_repolist'
        if not dnf_repos.exists():
            dnf_repos = base_path / 'sos_commands' / 'yum' / 'yum_-C_repolist'
        if dnf_repos.exists():
            data['repos'] = dnf_repos.read_text()
        
        # DNF/YUM config
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

    def analyze_containers(self, base_path: Path) -> dict:
        """Analyze container runtime information (docker/podman)."""
        Logger.debug("Analyzing container runtime information")
        analyzer = DockerCommandsAnalyzer(base_path)
        return analyzer.analyze()
