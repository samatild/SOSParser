"""
Supportconfig Network Interfaces Analyzer

Analyzes network interface information from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class InterfacesAnalyzer:
    """Analyzer for network interface information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract network interface information."""
        interfaces = {}

        # Get ip addr output
        ip_addr = self.parser.get_command_output('network.txt', '/sbin/ip addr')
        if ip_addr:
            interfaces['ip_addr'] = ip_addr

        # Link statistics
        ip_link = self.parser.get_command_output('network.txt', '/sbin/ip -stats link')
        if ip_link:
            interfaces['ip_link'] = ip_link

        # Wicked/network status
        wicked_status = self.parser.get_command_output('network.txt', '/bin/systemctl status network.service')
        if not wicked_status:
            wicked_status = self.parser.get_command_output('network.txt', '/bin/systemctl status wicked.service')
        if wicked_status:
            interfaces['status'] = wicked_status

        # Wicked detailed status/config
        wicked_ifstatus = self.parser.get_command_output('network.txt', '/usr/sbin/wicked ifstatus --verbose all')
        if wicked_ifstatus:
            interfaces['wicked_ifstatus'] = wicked_ifstatus
        wicked_show_config = self.parser.get_command_output('network.txt', '/usr/sbin/wicked show-config')
        if wicked_show_config:
            interfaces['wicked_show_config'] = wicked_show_config

        # Hardware info
        hwinfo = self.parser.get_command_output('network.txt', '/usr/sbin/hwinfo --netcard')
        if hwinfo:
            interfaces['hwinfo'] = hwinfo

        return interfaces
