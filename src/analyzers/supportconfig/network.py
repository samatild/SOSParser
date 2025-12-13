#!/usr/bin/env python3
"""Network analyzer for SUSE supportconfig."""

from pathlib import Path
from typing import Dict, Any
from .parser import SupportconfigParser
from .network_analyzers.interfaces import InterfacesAnalyzer
from .network_analyzers.routes import RoutesAnalyzer
from .network_analyzers.dns_config import DNSConfigAnalyzer
from .network_analyzers.hosts import HostsAnalyzer
from .network_analyzers.firewall import FirewallAnalyzer
from .network_analyzers.connectivity import ConnectivityAnalyzer


class SupportconfigNetwork:
    """Analyzer for supportconfig network information."""

    def __init__(self, root_path: Path):
        """
        Initialize network analyzer.

        Args:
            root_path: Path to extracted supportconfig directory
        """
        self.root_path = root_path
        self.parser = SupportconfigParser(root_path)

    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete network analysis.

        Returns:
            Dictionary with network information
        """
        routes = RoutesAnalyzer(self.root_path, self.parser).analyze()
        return {
            'interfaces': InterfacesAnalyzer(
                self.root_path, self.parser
            ).analyze(),
            'routes': routes,      # backward compatibility
            'routing': routes,     # matches template usage
            'dns': DNSConfigAnalyzer(self.root_path, self.parser).analyze(),
            'hosts': HostsAnalyzer(self.root_path, self.parser).analyze(),
            'firewall': FirewallAnalyzer(
                self.root_path, self.parser
            ).analyze(),
            'connectivity': ConnectivityAnalyzer(
                self.root_path, self.parser
            ).analyze(),
        }
