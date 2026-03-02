"""
Supportconfig SSSD Configuration Analyzer

Analyzes SSSD (System Security Services Daemon) configuration from sssd.txt.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class SSSDConfigAnalyzer:
    """Analyzer for SSSD configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract SSSD configuration from sssd.txt.

        Returns:
            Dictionary with verification, service_status, configs, domains
            for SSSD tab
        """
        sssd_info: Dict[str, Any] = {
            'verification_status': '',
            'verification_details': [],
            'service_status': {},
            'sssd_config': {},
            'domains': [],
            'nsswitch_config': {},
            'pam_config': [],
        }

        content = self.parser.read_file('sssd.txt')
        if not content:
            return sssd_info

        sections = self.parser.extract_sections(content)

        for section in sections:
            if section['type'] == 'Verification':
                lines = section['content'].split('\n')
                for line in lines:
                    if 'Verification Status:' in line:
                        sssd_info['verification_status'] = \
                            line.split(':', 1)[1].strip()
                    elif 'RPM Not Installed:' in line:
                        sssd_info['verification_status'] = 'Not Installed'
                        sssd_info['verification_details'].append(line.strip())
                    elif line and not line.startswith('#'):
                        sssd_info['verification_details'].append(line.strip())

            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()

                # Extract SSSD service status
                if 'systemctl status sssd' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('Loaded:'):
                            sssd_info['service_status']['loaded'] = \
                                line.split(':', 1)[1].strip()
                        elif line.startswith('Active:'):
                            sssd_info['service_status']['active'] = \
                                line.split(':', 1)[1].strip()
                        elif line.startswith('Main PID:'):
                            sssd_info['service_status']['pid'] = \
                                line.split(':', 1)[1].strip()

            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue

                file_path = lines[0].strip('# ').strip()

                # Extract SSSD configuration
                if ('/etc/sssd/sssd.conf' in file_path and
                        'not found' not in file_path.lower()):
                    current_domain = None
                    domain_config = {}

                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Check for domain section
                            if line.startswith('[') and line.endswith(']'):
                                # Save previous domain if exists
                                if current_domain and domain_config:
                                    sssd_info['domains'].append({
                                        'name': current_domain,
                                        'config': domain_config
                                    })
                                # Start new domain
                                current_domain = line[1:-1]
                                domain_config = {}
                            elif '=' in line and current_domain:
                                key, value = line.split('=', 1)
                                domain_config[key.strip()] = value.strip()
                            elif '=' in line:
                                key, value = line.split('=', 1)
                                sssd_info['sssd_config'][key.strip()] = \
                                    value.strip()

                    # Save last domain
                    if current_domain and domain_config:
                        sssd_info['domains'].append({
                            'name': current_domain,
                            'config': domain_config
                        })

                # Extract NSSwitch configuration
                elif ('/etc/nsswitch.conf' in file_path and
                        'not found' not in file_path.lower()):
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#') and ':' in line:
                            key, value = line.split(':', 1)
                            sssd_info['nsswitch_config'][key.strip()] = \
                                value.strip()

                # Extract PAM configuration for SSSD
                elif ('pam' in file_path.lower() and
                        'sssd' in file_path.lower() and
                        'not found' not in file_path.lower()):
                    pam_lines = []
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            pam_lines.append(line)
                    if pam_lines:
                        sssd_info['pam_config'].extend(pam_lines)

        return sssd_info
