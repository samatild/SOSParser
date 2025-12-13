"""
Supportconfig DNS Configuration Analyzer

Analyzes DNS configuration from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class DNSConfigAnalyzer:
    """Analyzer for DNS configuration."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract DNS configuration."""
        dns = {}

        # Prefer network.txt for DNS-related configuration
        net_content = self.parser.read_file('network.txt')
        if net_content:
            net_sections = self.parser.extract_sections(net_content)
            for section in net_sections:
                lines = section.get('content', '').split('\n')
                if not lines:
                    continue
                first = lines[0].strip()
                body = '\n'.join(lines[1:]).strip()
                if '/etc/resolv.conf' in first:
                    dns['resolv_conf'] = body
                elif '/etc/nsswitch.conf' in first:
                    dns['nsswitch'] = body
                elif '/etc/hosts' in first:
                    dns['hosts'] = body

        # Fallback to etc.txt for resolv.conf / nsswitch / hosts if missing
        if 'resolv_conf' not in dns:
            resolv_conf = self.parser.get_file_listing('etc.txt', '/etc/resolv.conf')
            if resolv_conf:
                dns['resolv_conf'] = resolv_conf
        if 'nsswitch' not in dns:
            nsswitch = self.parser.get_file_listing('etc.txt', '/etc/nsswitch.conf')
            if nsswitch:
                dns['nsswitch'] = nsswitch
        if 'hosts' not in dns:
            hosts = self.parser.get_file_listing('etc.txt', '/etc/hosts')
            if hosts:
                dns['hosts'] = hosts

        # Get nscd status
        nscd_status = self.parser.get_command_output('network.txt', 'systemctl status nscd.service')
        if nscd_status:
            dns['nscd_status'] = nscd_status

        return dns
