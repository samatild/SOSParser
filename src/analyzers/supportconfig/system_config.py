"""
Supportconfig System Configuration Analyzer

Analyzes system configuration from supportconfig format including:
- Boot and GRUB configuration
- SSH configuration
- Authentication settings
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from analyzers.docker import DockerCommandsAnalyzer
from .parser import SupportconfigParser


class SupportconfigSystemConfig:
    """Analyzer for supportconfig system configuration."""
    
    def __init__(self, root_path: Path):
        """Initialize with root path of extracted supportconfig."""
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)
    
    def analyze(self) -> Dict[str, Any]:
        """Run all system config analysis."""
        return {
            'general': self.get_general_config(),
            'boot': self.get_boot_config(),
            'ssh': self.get_ssh_config(),
            'services': self.get_services_config(),
            'cron': self.get_cron_config(),
            'security': self.get_security_config(),
            'packages': self.get_packages_config(),
            'kernel_modules': self.get_kernel_modules_config(),
            'containers': self.get_docker_config(),
        }
    
    def get_boot_config(self) -> Dict[str, Any]:
        """
        Extract boot and GRUB configuration from boot.txt for supportconfig.
        
        Returns:
            Dictionary shaped like the report template expects:
              - cmdline: kernel command line (from /proc/cmdline or GRUB default)
              - loader_entries: list of GRUB menu entries (names only)
              - grub_cfg: truncated grub.cfg content for quick inspection
              - grub_config: parsed /etc/default/grub key/value pairs (extra detail)
              - grub_verification: rpm -V status for grub2 (if present)
              - secure_boot: Secure Boot state (mokutil)
              - sbat_revocations: SBAT revocation list (mokutil)
              - efi_boot_current: current EFI boot entry
              - efi_boot_order: list of EFI boot order entries
              - efi_boot_entries: detailed EFI entries from efibootmgr -v
        """
        boot_info: Dict[str, Any] = {
            'cmdline': '',
            'loader_entries': [],
            'grub_cfg': '',
            'grub_config': {},
            'grub_cfg_path': '',
            'grub_verification': '',
            'secure_boot': '',
            'sbat_revocations': [],
            'efi_boot_current': '',
            'efi_boot_order': [],
            'efi_boot_entries': [],
        }

        content = self.parser.read_file('boot.txt')
        if not content:
            return boot_info

        sections = self.parser.extract_sections(content)

        def _parse_grub_cfg(lines: List[str]):
            """Parse grub.cfg content for menu entries and store truncated cfg."""
            if not lines:
                return
            # Store truncated grub.cfg (first 5000 chars to avoid bloating report)
            cfg_body = '\n'.join(lines[1:]).strip()
            if cfg_body:
                boot_info['grub_cfg'] = cfg_body[:5000]
            # Capture menuentry names
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("menuentry "):
                    # Format: menuentry 'NAME' ... {
                    name_part = stripped.split("menuentry", 1)[1].strip()
                    if name_part.startswith("'"):
                        name = name_part.split("'", 2)[1]
                        if name not in boot_info['loader_entries']:
                            boot_info['loader_entries'].append(name)

        for section in sections:
            if section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue

                header_line = lines[0].strip()
                header_lower = header_line.lower()

                # /etc/default/grub -> parse key/values for GRUB defaults
                if '/etc/default/grub' in header_line and 'not found' not in header_lower:
                    for line in lines[1:]:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"')
                            boot_info['grub_config'][key] = value
                            if key in ('GRUB_CMDLINE_LINUX_DEFAULT', 'GRUB_CMDLINE_LINUX'):
                                # Prefer GRUB default if cmdline not already set
                                if not boot_info['cmdline']:
                                    boot_info['cmdline'] = value

                # grub.cfg content and menu entries
                elif '/boot/grub2/grub.cfg' in header_line and 'not found' not in header_lower:
                    boot_info['grub_cfg_path'] = header_line
                    _parse_grub_cfg(lines)

                # /proc/cmdline -> running kernel command line
                elif '/proc/cmdline' in header_line and 'not found' not in header_lower:
                    cmdline = '\n'.join(lines[1:]).strip()
                    if cmdline:
                        boot_info['cmdline'] = cmdline

            elif section['type'] == 'Verification':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header_lower = lines[0].lower()
                # Capture rpm -V output for grub2
                if 'grub2' in header_lower:
                    for line in lines:
                        if 'Verification Status:' in line:
                            boot_info['grub_verification'] = line.split(':', 1)[1].strip()
                        elif line and not line.startswith('#'):
                            boot_info.setdefault('verification_details', []).append(line.strip())
            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()

                # Secure Boot state
                if 'mokutil --sb-state' in cmd_line:
                    state = '\n'.join(lines[1:]).strip()
                    if state:
                        boot_info['secure_boot'] = state

                # SBAT revocations
                elif 'mokutil --list-sbat-revocations' in cmd_line:
                    revos = [l.strip() for l in lines[1:] if l.strip()]
                    if revos:
                        boot_info['sbat_revocations'] = revos

                # EFI boot manager info
                elif 'efibootmgr -v' in cmd_line:
                    for line in lines[1:]:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('BootCurrent:'):
                            boot_info['efi_boot_current'] = line.split(':', 1)[1].strip()
                        elif line.startswith('BootOrder:'):
                            order = line.split(':', 1)[1].strip()
                            boot_info['efi_boot_order'] = [o.strip() for o in order.split(',') if o.strip()]
                        elif line.startswith('Boot'):
                            # Keep the full line for context
                            boot_info['efi_boot_entries'].append(line)

        return boot_info
    
    def get_ssh_config(self) -> Dict[str, Any]:
        """
        Extract SSH and authentication configuration from ssh.txt.
        
        Returns:
            Dictionary with verification, service_status, configs, ports, PAM
        """
        ssh_info: Dict[str, Any] = {
            'verification_status': '',
            'verification_details': [],
            'service_status': {},
            'sshd_config': {},
            'ssh_client_config': {},
            'pam_config': [],
            'listening_ports': [],
        }
        
        content = self.parser.read_file('ssh.txt')
        if not content:
            return ssh_info
        
        sections = self.parser.extract_sections(content)
        
        for section in sections:
            if section['type'] == 'Verification':
                lines = section['content'].split('\n')
                for line in lines:
                    if 'Verification Status:' in line:
                        ssh_info['verification_status'] = line.split(':', 1)[1].strip()
                    elif line and not line.startswith('#'):
                        ssh_info['verification_details'].append(line.strip())

            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()
                
                # Extract SSH service status
                if 'systemctl status sshd' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('Loaded:'):
                            ssh_info['service_status']['loaded'] = line.split(':', 1)[1].strip()
                        elif line.startswith('Active:'):
                            ssh_info['service_status']['active'] = line.split(':', 1)[1].strip()
                        elif line.startswith('Main PID:'):
                            ssh_info['service_status']['pid'] = line.split(':', 1)[1].strip()
                
                # Extract listening ports
                elif 'ss -nlp' in cmd_line or 'grep sshd' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    for line in output.split('\n'):
                        if 'sshd' in line and line.strip():
                            ssh_info['listening_ports'].append(line.strip())
            
            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                
                file_path = lines[0].strip('# ').strip()
                
                # Extract sshd_config
                if '/etc/ssh/sshd_config' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                key, value = parts
                                ssh_info['sshd_config'][key] = value
                            elif parts:
                                ssh_info['sshd_config'][parts[0]] = 'enabled'
                
                # Extract ssh_config (client)
                elif '/etc/ssh/ssh_config' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('Host'):
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                key, value = parts
                                ssh_info['ssh_client_config'][key] = value
                
                # Extract PAM config
                elif '/etc/pam.d/sshd' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            ssh_info['pam_config'].append(line)
        
        return ssh_info

    def get_services_config(self) -> Dict[str, Any]:
        """
        Extract basic systemd service status from systemd-status.txt.
        
        Returns:
            Dictionary with:
              - entries: list of service dicts (name, desc, loaded, active, pid, cmd)
              - failed_services: list of entries where Active indicates failure/inactive
        """
        services: Dict[str, Any] = {
            'entries': [],
            'failed_services': [],
        }

        content = self.parser.read_file('systemd-status.txt')
        if not content:
            return services

        sections = self.parser.extract_sections(content)

        for section in sections:
            if section['type'] != 'Command':
                continue
            lines = section['content'].split('\n')
            if not lines:
                continue
            header = lines[0].strip('# ').strip()
            service_name = ''
            if 'systemctl status' in header:
                # Extract service name from the command
                parts = header.split('status', 1)
                if len(parts) > 1:
                    service_name = parts[1].strip().strip("'\"")
            # Fallback to unknown if not extracted
            if not service_name:
                service_name = '(unknown)'

            service_desc = ''
            loaded = ''
            active = ''
            main_pid = ''

            for line in lines[1:]:
                stripped = line.strip()
                if not stripped:
                    continue
                # First bullet line: "● name.service - Description"
                if stripped.startswith('●'):
                    bullet = stripped.lstrip('●').strip()
                    if ' - ' in bullet:
                        maybe_name, maybe_desc = bullet.split(' - ', 1)
                        service_desc = maybe_desc.strip()
                        # Use the name from the bullet if it looks like a service
                        if maybe_name.endswith('.service'):
                            service_name = maybe_name.strip()
                    continue
                if stripped.startswith('Loaded:'):
                    loaded = stripped.split(':', 1)[1].strip()
                elif stripped.startswith('Active:'):
                    active = stripped.split(':', 1)[1].strip()
                elif stripped.startswith('Main PID:'):
                    main_pid = stripped.split(':', 1)[1].strip()

            entry = {
                'name': service_name,
                'description': service_desc,
                'loaded': loaded,
                'active': active,
                'main_pid': main_pid,
                'command': header,
            }
            services['entries'].append(entry)

            active_lower = active.lower()
            if 'failed' in active_lower or 'inactive' in active_lower:
                services['failed_services'].append(entry)

        return services

    def get_cron_config(self) -> Dict[str, Any]:
        """
        Extract cron/at scheduler configuration from cron.txt.
        
        Returns a dictionary with:
          - cron_verification_status
          - cron_service (loaded/active/pid)
          - cron_dirs: mapping of cron.* dirs to file lists
          - crontab: /etc/crontab contents
          - at_verification_status
          - at_service (loaded/active/pid)
          - at_jobs: list of job files
        """
        data: Dict[str, Any] = {
            'cron_verification_status': '',
            'cron_service': {},
            'cron_dirs': {},
            'crontab': '',
            'at_verification_status': '',
            'at_service': {},
            'at_jobs': [],
            'at_jobs_content': {},
        }

        content = self.parser.read_file('cron.txt')
        if not content:
            return data

        sections = self.parser.extract_sections(content)

        def _parse_systemctl(lines):
            info = {}
            for line in lines:
                line = line.strip()
                if line.startswith('Loaded:'):
                    info['loaded'] = line.split(':', 1)[1].strip()
                elif line.startswith('Active:'):
                    info['active'] = line.split(':', 1)[1].strip()
                elif line.startswith('Main PID:'):
                    info['pid'] = line.split(':', 1)[1].strip()
            return info

        for section in sections:
            if section['type'] == 'Verification':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header = lines[0].lower()
                for line in lines:
                    if 'Verification Status:' in line:
                        status = line.split(':', 1)[1].strip()
                        if 'cronie' in header:
                            data['cron_verification_status'] = status
                        elif 'at-' in header or ' at-' in header:
                            data['at_verification_status'] = status

            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()

                if 'systemctl status cron.service' in cmd_line:
                    data['cron_service'] = _parse_systemctl(lines[1:])
                elif 'systemctl status atd.service' in cmd_line:
                    data['at_service'] = _parse_systemctl(lines[1:])
                elif 'find -L /etc/cron.' in cmd_line:
                    dir_name = cmd_line.split()[-1].rstrip('/').split('/')[-1]
                    files = [l.strip() for l in lines[1:] if l.strip()]
                    data['cron_dirs'][dir_name] = files
                elif 'find /var/spool/atjobs/' in cmd_line:
                    jobs = [l.strip() for l in lines[1:] if l.strip()]
                    data['at_jobs'].extend(jobs)

            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header = lines[0].strip()
                if '/etc/crontab' in header and 'not found' not in header.lower():
                    data['crontab'] = '\n'.join(lines[1:]).strip()
                elif '/var/spool/atjobs/' in header and 'not found' not in header.lower():
                    content_str = '\n'.join(lines[1:]).strip()
                    data['at_jobs_content'][header] = content_str

        return data

    def get_security_config(self) -> Dict[str, Any]:
        """
        Extract SELinux/AppArmor/Audit info from supportconfig security files.
        """
        security: Dict[str, Any] = {
            'selinux_status': '',
            'apparmor': {
                'verification': [],
                'service': {},
                'aa_status': '',
                'parser_conf': '',
                'log_excerpt': '',
                'missing_packages': [],
            },
            'audit': {
                'verification_status': '',
                'service': {},
                'auditctl_status': '',
                'auditctl_rules': '',
                'aureport_summary': '',
                'rules': {},
                'auditd_conf': '',
                'audit_log_excerpt': '',
            },
        }

        # SELinux
        selinux_content = self.parser.read_file('security-selinux.txt')
        if selinux_content:
            sections = self.parser.extract_sections(selinux_content)
            for section in sections:
                if section['type'] == 'Verification':
                    lines = section['content'].split('\n')
                    for line in lines:
                        if 'Verification Status' in line or 'RPM Not Installed' in line:
                            security['selinux_status'] = line.strip('# ').strip()
                            break

        # AppArmor
        apparmor_content = self.parser.read_file('security-apparmor.txt')
        if apparmor_content:
            sections = self.parser.extract_sections(apparmor_content)
            for section in sections:
                if section['type'] == 'Verification':
                    lines = section['content'].split('\n')
                    if lines:
                        first = lines[0].lower()
                        status_line = next(
                            (l for l in lines if 'Verification Status' in l),
                            None
                        )
                        if 'not installed' in lines[0].lower():
                            security['apparmor']['missing_packages'].append(lines[0].strip('# ').strip())
                        elif status_line:
                            security['apparmor']['verification'].append(status_line.strip())
                        else:
                            security['apparmor']['verification'].extend([l for l in lines if l])

                elif section['type'] == 'Command':
                    lines = section['content'].split('\n')
                    if not lines:
                        continue
                    cmd = lines[0].strip('# ').strip()
                    if 'systemctl status apparmor.service' in cmd:
                        info = {}
                        for line in lines[1:]:
                            line = line.strip()
                            if line.startswith('Loaded:'):
                                info['loaded'] = line.split(':', 1)[1].strip()
                            elif line.startswith('Active:'):
                                info['active'] = line.split(':', 1)[1].strip()
                            elif line.startswith('Main PID:'):
                                info['pid'] = line.split(':', 1)[1].strip()
                        security['apparmor']['service'] = info
                    elif 'aa-status' in cmd:
                        status_text = '\n'.join(lines[1:]).strip()
                        if status_text:
                            security['apparmor']['aa_status'] = status_text

                elif section['type'] == 'Configuration':
                    lines = section['content'].split('\n')
                    if lines and '/etc/apparmor/parser.conf' in lines[0]:
                        security['apparmor']['parser_conf'] = '\n'.join(lines[1:]).strip()

                elif section['type'] == 'Log':
                    # Capture a short excerpt from audit log
                    excerpt = '\n'.join(section['content'].split('\n')[:30]).strip()
                    security['apparmor']['log_excerpt'] = excerpt

        # Audit
        audit_content = self.parser.read_file('security-audit.txt')
        if audit_content:
            sections = self.parser.extract_sections(audit_content)
            for section in sections:
                if section['type'] == 'Verification':
                    lines = section['content'].split('\n')
                    for line in lines:
                        if 'Verification Status:' in line:
                            security['audit']['verification_status'] = line.split(':', 1)[1].strip()
                            break

                elif section['type'] == 'Command':
                    lines = section['content'].split('\n')
                    if not lines:
                        continue
                    cmd = lines[0].strip('# ').strip()
                    if 'systemctl status auditd.service' in cmd:
                        info = {}
                        for line in lines[1:]:
                            line = line.strip()
                            if line.startswith('Loaded:'):
                                info['loaded'] = line.split(':', 1)[1].strip()
                            elif line.startswith('Active:'):
                                info['active'] = line.split(':', 1)[1].strip()
                            elif line.startswith('Main PID:'):
                                info['pid'] = line.split(':', 1)[1].strip()
                        security['audit']['service'] = info
                    elif 'auditctl -s' in cmd:
                        security['audit']['auditctl_status'] = '\n'.join(lines[1:]).strip()
                    elif 'auditctl -l' in cmd:
                        security['audit']['auditctl_rules'] = '\n'.join(lines[1:]).strip()
                    elif 'aureport' in cmd:
                        security['audit']['aureport_summary'] = '\n'.join(lines[1:]).strip()

                elif section['type'] == 'Configuration':
                    lines = section['content'].split('\n')
                    if not lines:
                        continue
                    header = lines[0]
                    body = '\n'.join(lines[1:]).strip()
                    if '/etc/audit/auditd.conf' in header:
                        security['audit']['auditd_conf'] = body
                    elif '/etc/audit/' in header or '/etc/audit/rules.d/' in header:
                        security['audit']['rules'][header] = body

                elif section['type'] == 'Log':
                    excerpt = '\n'.join(section['content'].split('\n')[:50]).strip()
                    security['audit']['audit_log_excerpt'] = excerpt

        return security

    def get_packages_config(self) -> Dict[str, Any]:
        """
        Summarize installed RPMs from rpm.txt.
        """
        packages: Dict[str, Any] = {
            'rpm_count': 0,
            'rpm_sample': [],
            'repos': '',
            'package_manager_conf': '',
        }

        content = self.parser.read_file('rpm.txt')
        if not content:
            return packages

        sections = self.parser.extract_sections(content)
        rpm_entries: List[str] = []

        for section in sections:
            if section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd = lines[0].strip('# ').strip()
                # Full rpm list
                if 'rpm -qa --queryformat "%-35{NAME}' in cmd:
                    # Skip header line if present
                    for line in lines[1:]:
                        line = line.strip()
                        if not line or line.startswith('NAME '):
                            continue
                        rpm_entries.append(line)
                # Repo list (if present)
                elif 'zypper lr' in cmd or 'zypper repos' in cmd:
                    repo_body = '\n'.join(lines[1:]).strip()
                    if repo_body:
                        packages['repos'] = repo_body
                # Package manager conf (e.g., zypper.conf) - none in this file, placeholder if added later

        if rpm_entries:
            packages['rpm_count'] = len(rpm_entries)
            packages['rpm_sample'] = rpm_entries[:50]

        return packages

    def get_kernel_modules_config(self) -> Dict[str, Any]:
        """
        Capture kernel-related info from env.txt (sysctl, ulimit, etc.).
        """
        data: Dict[str, Any] = {
            'sysctl_all': '',
            'sysctl_files': {},
            'sysctl_service': {},
            'ulimit': '',
            'lsmod': '',
            'modprobe_d': {},
        }

        content = self.parser.read_file('env.txt')
        if not content:
            return data

        sections = self.parser.extract_sections(content)

        def _parse_systemctl(lines):
            info = {}
            for line in lines:
                line = line.strip()
                if line.startswith('Loaded:'):
                    info['loaded'] = line.split(':', 1)[1].strip()
                elif line.startswith('Active:'):
                    info['active'] = line.split(':', 1)[1].strip()
                elif line.startswith('Main PID:'):
                    info['pid'] = line.split(':', 1)[1].strip()
            return info

        for section in sections:
            if section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd = lines[0].strip('# ').strip()
                if cmd.startswith('ulimit'):
                    data['ulimit'] = '\n'.join(lines[1:]).strip()
                elif 'systemctl status systemd-sysctl.service' in cmd:
                    data['sysctl_service'] = _parse_systemctl(lines[1:])
                elif '/sbin/sysctl -a' in cmd or 'sysctl -a' in cmd:
                    data['sysctl_all'] = '\n'.join(lines[1:]).strip()

            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                header = lines[0].strip()
                body = '\n'.join(lines[1:]).strip()
                if 'sysctl' in header:
                    data['sysctl_files'][header] = body

        return data

    def get_docker_config(self) -> Dict[str, Any]:
        """
        Parse docker information from sos_commands/docker when present.
        """
        analyzer = DockerCommandsAnalyzer(self.root_path)
        return analyzer.analyze()

    def get_general_config(self) -> Dict[str, Any]:
        """
        Populate general tab from basic-environment.txt and basic-health-check.txt.
        """
        general: Dict[str, Any] = {}

        # basic-environment.txt
        env_content = self.parser.read_file('basic-environment.txt')
        if env_content:
            sections = self.parser.extract_sections(env_content)
            for section in sections:
                if section['type'] == 'Command':
                    lines = section['content'].split('\n')
                    if not lines:
                        continue
                    cmd = lines[0].strip('# ').strip()
                    if cmd == '/bin/date':
                        general['collection_time'] = '\n'.join(lines[1:]).strip()
                    elif cmd == '/bin/uname -a':
                        general['uname'] = '\n'.join(lines[1:]).strip()
                elif section['type'] == 'System':
                    # virtualization section body
                    text = section['content'].strip()
                    if text:
                        general['virtualization'] = text
                elif section['type'] == 'Configuration':
                    lines = section['content'].split('\n')
                    if lines and '/etc/os-release' in lines[0]:
                        general['os_release'] = '\n'.join(lines[1:]).strip()
                elif section['type'] == 'Verification':
                    # Example: RPM Not Installed: firewalld
                    text = section['content'].strip()
                    if text:
                        general.setdefault('verifications', []).append(text)

        # basic-health-check.txt
        health_content = self.parser.read_file('basic-health-check.txt')
        if health_content:
            sections = self.parser.extract_sections(health_content)
            for section in sections:
                lines = section['content'].split('\n')
                if not lines:
                    continue
                if section['type'] == 'Command':
                    cmd = lines[0].strip('# ').strip()
                    body = '\n'.join(lines[1:]).strip()
                    if '/usr/bin/uptime' in cmd:
                        general['uptime'] = body
                    elif 'cpu/vulnerabilities' in cmd:
                        general['cpu_vulnerabilities'] = body
                    elif 'vmstat' in cmd:
                        general['vmstat'] = body
                    elif cmd.startswith('/usr/bin/free'):
                        general['free'] = body
                    elif cmd.startswith('/bin/df -h'):
                        general['df_h'] = body
                    elif cmd.startswith('/bin/df -i'):
                        general['df_i'] = body
                    elif cmd.startswith('/bin/ps axwwo'):
                        # avoid full process list; keep top part
                        general['ps_ax'] = '\n'.join(lines[:40]).strip()
                elif section['type'] == 'Configuration':
                    if '/proc/sys/kernel/tainted' in lines[0]:
                        general['kernel_tainted'] = '\n'.join(lines[1:]).strip()
                elif section['type'] == 'Summary':
                    # Top processes summaries
                    header = section['header'].lower()
                    body = section['content'].strip()
                    if 'cpu' in header:
                        general['top_cpu'] = body
                    elif 'memory' in header:
                        general['top_mem'] = body

        return general
