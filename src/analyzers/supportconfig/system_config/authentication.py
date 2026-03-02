"""
Supportconfig Authentication Configuration Analyzer

Analyzes SSH and authentication configuration from ssh.txt.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class AuthenticationConfigAnalyzer:
    """Analyzer for SSH and authentication configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract SSH and authentication configuration from ssh.txt.

        Returns:
            Dictionary with verification, service_status, configs, ports, PAM for authentication tab
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
