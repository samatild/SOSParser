"""
Supportconfig NTP Configuration Analyzer

Analyzes NTP (Network Time Protocol) configuration from ntp.txt.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class NTPConfigAnalyzer:
    """Analyzer for NTP configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """
        Extract NTP configuration from ntp.txt.

        Returns:
            Dictionary with verification, service_status, configs, servers for NTP tab
        """
        ntp_info: Dict[str, Any] = {
            'verification_status': '',
            'verification_details': [],
            'service_status': {},
            'ntp_config': {},
            'chrony_config': {},
            'timesyncd_config': {},
            'servers': [],
            'pools': [],
            'chronyc_sources': '',
            'chronyc_sourcestats': '',
            'chronyc_tracking': '',
            'chronyc_activity': '',
            'timedatectl_status': '',
        }

        content = self.parser.read_file('ntp.txt')
        if not content:
            return ntp_info

        sections = self.parser.extract_sections(content)

        for section in sections:
            if section['type'] == 'Verification':
                lines = section['content'].split('\n')
                for line in lines:
                    if 'Verification Status:' in line:
                        ntp_info['verification_status'] = line.split(':', 1)[1].strip()
                    elif 'RPM Not Installed:' in line:
                        ntp_info['verification_status'] = 'Not Installed'
                        ntp_info['verification_details'].append(line.strip())
                    elif line and not line.startswith('#'):
                        ntp_info['verification_details'].append(line.strip())

            elif section['type'] == 'Command':
                lines = section['content'].split('\n')
                if not lines:
                    continue
                cmd_line = lines[0].strip('# ').strip()

                # Extract NTP/Chrony service status
                if 'systemctl status' in cmd_line and ('ntp' in cmd_line or 'chrony' in cmd_line):
                    output = '\n'.join(lines[1:]).strip()
                    service_name = 'chronyd' if 'chrony' in cmd_line else 'ntpd'
                    ntp_info['service_status'][service_name] = {}
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('Loaded:'):
                            ntp_info['service_status'][service_name]['loaded'] = \
                                line.split(':', 1)[1].strip()
                        elif line.startswith('Active:'):
                            ntp_info['service_status'][service_name]['active'] = \
                                line.split(':', 1)[1].strip()
                        elif line.startswith('Main PID:'):
                            ntp_info['service_status'][service_name]['pid'] = \
                                line.split(':', 1)[1].strip()

                # Extract timedatectl status
                elif 'timedatectl' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    ntp_info['timedatectl_status'] = output
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('NTP service:'):
                            ntp_info['ntp_service'] = line.split(':', 1)[1].strip()
                        elif line.startswith('RTC in local TZ:'):
                            ntp_info['rtc_local_tz'] = line.split(':', 1)[1].strip()

                # Extract chronyc sources
                elif 'chronyc -n sources' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    ntp_info['chronyc_sources'] = output
                    # Parse sources to extract server information
                    self._parse_chronyc_sources(output, ntp_info)

                # Extract chronyc sourcestats
                elif 'chronyc -n sourcestats' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    ntp_info['chronyc_sourcestats'] = output

                # Extract chronyc tracking
                elif 'chronyc -n tracking' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    ntp_info['chronyc_tracking'] = output

                # Extract chronyc activity
                elif 'chronyc activity' in cmd_line:
                    output = '\n'.join(lines[1:]).strip()
                    ntp_info['chronyc_activity'] = output

            elif section['type'] == 'Configuration':
                lines = section['content'].split('\n')
                if not lines:
                    continue

                file_path = lines[0].strip('# ').strip()

                # Extract Chrony configuration
                if '/etc/chrony.conf' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.startswith('server ') or line.startswith('peer '):
                                parts = line.split(None, 1)
                                if len(parts) == 2:
                                    server_type, server_addr = parts
                                    ntp_info['servers'].append({
                                        'type': server_type,
                                        'address': server_addr,
                                        'source': 'chrony'
                                    })
                            elif line.startswith('pool '):
                                parts = line.split(None, 1)
                                if len(parts) == 2:
                                    _, pool_addr = parts
                                    ntp_info['pools'].append({
                                        'address': pool_addr,
                                        'source': 'chrony'
                                    })
                            else:
                                # Parse other chrony directives
                                # Handle directives with values separated by spaces or equals
                                parts = line.split(None, 1)
                                if len(parts) == 2:
                                    directive, value = parts
                                    # Clean up value if it has comments
                                    value = value.split('#')[0].strip()
                                    ntp_info['chrony_config'][directive] = value
                                elif len(parts) == 1:
                                    # Single word directives
                                    ntp_info['chrony_config'][parts[0]] = 'enabled'

                # Extract NTP configuration
                elif '/etc/ntp.conf' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.startswith('server ') or line.startswith('peer '):
                                parts = line.split(None, 1)
                                if len(parts) == 2:
                                    server_type, server_addr = parts
                                    ntp_info['servers'].append({
                                        'type': server_type,
                                        'address': server_addr,
                                        'source': 'ntp'
                                    })
                            elif line.startswith('pool '):
                                parts = line.split(None, 1)
                                if len(parts) == 2:
                                    _, pool_addr = parts
                                    ntp_info['pools'].append({
                                        'address': pool_addr,
                                        'source': 'ntp'
                                    })
                            elif '=' in line:
                                key, value = line.split('=', 1)
                                ntp_info['ntp_config'][key.strip()] = value.strip()

                # Extract systemd-timesyncd configuration
                elif '/etc/systemd/timesyncd.conf' in file_path and 'not found' not in file_path.lower():
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            ntp_info['timesyncd_config'][key.strip()] = value.strip()

        return ntp_info

    def _parse_chronyc_sources(self, output: str, ntp_info: Dict[str, Any]):
        """Parse chronyc sources output to extract NTP server information."""
        lines = output.split('\n')
        in_table = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for the table header to know when we start parsing sources
            if 'MS Name/IP address' in line:
                in_table = True
                continue

            if in_table and line and not line.startswith('===') and len(line.split()) >= 2:
                # Parse source lines like: ^- 85.199.214.98 ...
                parts = line.split()
                if len(parts) >= 2:
                    mode = parts[0]  # ^, =, #, etc.
                    address = parts[1]  # IP address or hostname

                    # Determine source type from mode
                    if mode.startswith('^'):
                        source_type = 'server'
                    elif mode.startswith('='):
                        source_type = 'peer'
                    elif mode.startswith('#'):
                        source_type = 'local_clock'
                    else:
                        source_type = 'unknown'

                    # Add to servers list if it's a network source
                    if source_type in ['server', 'peer']:
                        ntp_info['servers'].append({
                            'type': source_type,
                            'address': address,
                            'source': 'chronyc_sources',
                            'mode': mode
                        })