"""
Supportconfig Network Routes Analyzer

Analyzes routing information from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class RoutesAnalyzer:
    """Analyzer for routing information."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> Dict[str, Any]:
        """Extract routing information."""
        routes = {}

        # Get ip route outputs
        ip_route = self.parser.get_command_output('network.txt', '/sbin/ip route')
        if ip_route:
            routes['ip_route'] = ip_route
        ip_route_v6 = self.parser.get_command_output('network.txt', '/sbin/ip -6 route')
        if ip_route_v6:
            routes['ip6_route'] = ip_route_v6
        local_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table local')
        if local_route:
            routes['route_table_local'] = local_route
        main_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table main')
        if main_route:
            routes['route_table_main'] = main_route
        default_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table default')
        if default_route:
            routes['route_table_default'] = default_route
        cache_route = self.parser.get_command_output('network.txt', '/sbin/ip route show table cache')
        if cache_route:
            routes['route_table_cache'] = cache_route
        cache_route_v6 = self.parser.get_command_output('network.txt', '/sbin/ip -6 route show table cache')
        if cache_route_v6:
            routes['route_table_cache_v6'] = cache_route_v6

        return routes
