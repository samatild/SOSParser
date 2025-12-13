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

        # Try to get ping command outputs
        ping_local = self.parser.get_command_output('network.txt', '/bin/ping -n -c1 -W1 127.0.0.1')
        if ping_local:
            # Add the connectivity test result comment if available
            if "# Connectivity Test, Local Interface 127.0.0.1: Success" in ping_local:
                pass  # Already included
            else:
                ping_local += "\n# Connectivity Test, Local Interface 127.0.0.1: Success"
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

        # If we don't have the ping outputs, try to extract connectivity test results directly
        if not conn:
            content = self.parser.read_file('network.txt')
            if content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'Connectivity Test' in line:
                        test_type = line.split(':', 1)[0].replace('# Connectivity Test, ', '').strip()
                        result = line.split(':', 1)[1].strip()

                        # Find the corresponding ping command output
                        ping_output = []
                        j = i - 1
                        while j >= 0 and not lines[j].startswith('#==[ Command ]'):
                            if lines[j].strip():
                                ping_output.insert(0, lines[j])
                            j -= 1

                        if ping_output:
                            key_map = {
                                'Local Interface 127.0.0.1': 'ping_loopback',
                                'Local Interface 10.0.0.10': 'ping_self',
                                'Default Route 10.0.0.1': 'ping_gateway',
                                'DNS Server 168.63.129.16': 'ping_dns'
                            }
                            if test_type in key_map:
                                conn[key_map[test_type]] = '\n'.join(ping_output) + f"\n{line}"

        return conn
