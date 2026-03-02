"""
Supportconfig Security Configuration Analyzer

Analyzes SELinux/AppArmor/Audit configuration from security files.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class SecurityConfigAnalyzer:
    """Analyzer for security configuration (SELinux, AppArmor, Audit)."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
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
