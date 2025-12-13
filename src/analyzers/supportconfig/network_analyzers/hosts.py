"""
Supportconfig Hosts Analyzer

Analyzes /etc/hosts file from supportconfig data.
"""

from typing import Dict, Any
from pathlib import Path
from ..parser import SupportconfigParser


class HostsAnalyzer:
    """Analyzer for /etc/hosts file."""

    def __init__(self, root_path: Path, parser: SupportconfigParser):
        """Initialize with root path and parser."""
        self.root_path = root_path
        self.parser = parser

    def analyze(self) -> str:
        """Extract /etc/hosts file."""
        hosts = self.parser.get_file_listing('etc.txt', '/etc/hosts')
        return hosts if hosts else ""
