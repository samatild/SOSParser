"""
Supportconfig Connectivity Analyzer

Analyzes connectivity tests (ping) from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class ConnectivityAnalyzer:
    """Analyzer for connectivity tests."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract connectivity tests (ping) from network.txt."""
        conn = {}
        ping_local = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 127.0.0.1')
        if ping_local:
            conn['ping_loopback'] = ping_local
        ping_self = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 10.0.0.10')
        if ping_self:
            conn['ping_self'] = ping_self
        ping_gateway = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 10.0.0.1')
        if ping_gateway:
            conn['ping_gateway'] = ping_gateway
        ping_dns = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 168.63.129.16')
        if ping_dns:
            conn['ping_dns'] = ping_dns
        return conn
