"""
Supportconfig Firewall Analyzer

Analyzes firewall information from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class FirewallAnalyzer:
    """Analyzer for firewall information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract firewall information."""
        firewall = {}

        # Try to get firewalld status (may be missing in supportconfig)
        firewalld_status = self.parser.get_command_output('network.txt', 'firewall-cmd --state')
        if not firewalld_status:
            firewalld_status = self.parser.get_command_output('network.txt', 'systemctl status firewalld')
        if firewalld_status:
            firewall['firewalld'] = firewalld_status

        # iptables / ip6tables outputs; in this supportconfig they are notes about modules
        iptables = self.parser.get_command_output('network.txt', 'iptables')
        if iptables:
            firewall['iptables'] = iptables
        ip6tables = self.parser.get_command_output('network.txt', 'ip6tables')
        if ip6tables:
            firewall['ip6tables'] = ip6tables

        return firewall
